import sys
import time

import pytest
import numpy as np

import ray
from ray.exceptions import OwnerDiedError


# https://github.com/ray-project/ray/issues/19659
def test_owner_assign_bug(ray_start_regular):
    @ray.remote
    class Owner:
        pass

    owner = Owner.remote()

    @ray.remote
    class Executor:
        def f(self):
            x = [ray.put("World", _owner=owner)]
            print("World id:", x)
            return x

    e = Executor.remote()
    [ref] = ray.get(e.f.remote())

    time.sleep(1)
    del e  # <------ this also seems to delete the "World" object
    time.sleep(1)

    print("Hello", ray.get(ref))


@pytest.mark.parametrize(
    "actor_resources",
    [
        dict(zip(["owner", "creator", "borrower"], [{f"node{i}": 1} for i in _]))
        for _ in [
            [1, 2, 3],  # None of them is on the same node.
            [1, 1, 3],  # Owner and creator are on the same node.
            [3, 2, 3],  # Owner and borrower are on the same node.
            [1, 3, 3],  # Creator and borrower are on the same node.
            [3, 3, 3],  # All of them are on the same node.
        ]
    ],
)
def test_owner_assign_when_put(ray_start_cluster, actor_resources):
    cluster_node_config = [
        {"num_cpus": 1, "resources": {f"node{i+1}": 10}} for i in range(3)
    ]
    cluster = ray_start_cluster
    for kwargs in cluster_node_config:
        cluster.add_node(**kwargs)
    ray.init(address=cluster.address)

    @ray.remote(resources=actor_resources["creator"], num_cpus=0)
    class Creator:
        def gen_object_ref(self, data="test", owner=None):
            return ray.put(data, _owner=owner)

    @ray.remote(resources=actor_resources["owner"], num_cpus=0)
    class Owner:
        def __init__(self):
            self.ref = None

        def set_object_ref(self, ref):
            self.ref = ref

        def warmup(self):
            return 0

    @ray.remote(resources=actor_resources["borrower"], num_cpus=0)
    class Borrower:
        def get_object(self, ref):
            return ray.get(ref)

    owner = Owner.remote()
    creator = Creator.remote()
    borrower = Borrower.remote()

    # Make sure the owner actor is alive.
    ray.get(owner.warmup.remote())

    object_ref = creator.gen_object_ref.remote(data="test1", owner=owner)
    # TODO(Catch-Bull): Ideally, deleting this line can also work normally,
    # cause driver keep a reference of the object. But, for now, it still
    # requires the owner to keep a reference of the object to make it
    # available.
    ray.get(owner.set_object_ref.remote(object_ref))

    ray.kill(creator)
    time.sleep(10)

    data = ray.get(borrower.get_object.remote(object_ref))
    assert data == "test1"

    ray.kill(owner)
    time.sleep(2)
    with pytest.raises(ray.exceptions.RayTaskError) as error:
        ray.get(borrower.get_object.remote(object_ref), timeout=2)
    assert isinstance(error.value.as_instanceof_cause(), OwnerDiedError)


def test_multiple_objects(ray_start_cluster):
    cluster_node_config = [
        {"num_cpus": 1, "resources": {f"node{i+1}": 10}} for i in range(3)
    ]
    cluster = ray_start_cluster
    for kwargs in cluster_node_config:
        cluster.add_node(**kwargs)
    ray.init(address=cluster.address)

    OBJECT_NUMBER = 1000

    @ray.remote(resources={"node1": 1}, num_cpus=0)
    class Creator:
        def gen_object_refs(self, owner):
            refs = []
            for _ in range(OBJECT_NUMBER):
                refs.append(ray.put(np.random.rand(2, 2), _owner=owner))
            ray.get(owner.set_object_refs.remote(refs))

    @ray.remote(resources={"node2": 1}, num_cpus=0)
    class Owner:
        def __init__(self):
            self.refs = None

        def set_object_refs(self, refs):
            self.refs = refs

        def warmup(self):
            return 0

        def remote_get_object_refs(self, worker):
            return ray.get(worker.get_objects.remote(self.refs))

    @ray.remote(resources={"node3": 1}, num_cpus=0)
    class Borrower:
        def get_objects(self, refs):
            for ref in refs:
                ray.get(ref)
            return True

    owner = Owner.remote()
    creator = Creator.remote()
    borrower = Borrower.remote()

    # Make sure the owner actor is alive.
    ray.get(owner.warmup.remote())

    ray.get(creator.gen_object_refs.remote(owner))

    ray.kill(creator)

    assert ray.get(owner.remote_get_object_refs.remote(borrower), timeout=60)


@pytest.mark.skipif(sys.platform == "win32", reason="Failing on Windows.")
def test_owner_assign_inner_object(shutdown_only):
    @ray.remote
    class Owner:
        def warmup(self):
            pass

    @ray.remote
    def get_borrowed_object():
        ref = ray.put(("test_borrowed"))
        return [ref]

    owner = Owner.remote()
    ray.get(owner.warmup.remote())

    class OutObject:
        def __init__(self, owned_inner_ref, borrowed_inner_ref):
            self.owned_inner_ref = owned_inner_ref
            self.borrowed_inner_ref = borrowed_inner_ref

    owned_inner_ref = ray.put("test_owned")

    borrowed_inner_ref = ray.get(get_borrowed_object.remote())[0]
    out_ref = ray.put(OutObject(owned_inner_ref, borrowed_inner_ref), _owner=owner)

    # wait enough time to delete data when the reference count is lower
    # than expected
    del owned_inner_ref, borrowed_inner_ref
    time.sleep(10)

    assert ray.get(ray.get(out_ref).owned_inner_ref) == "test_owned"
    assert ray.get(ray.get(out_ref).borrowed_inner_ref) == "test_borrowed"


if __name__ == "__main__":
    sys.exit(pytest.main(["-sv", __file__]))
