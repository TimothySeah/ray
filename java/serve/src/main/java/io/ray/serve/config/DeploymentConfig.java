package io.ray.serve.config;

import com.google.common.base.Preconditions;
import com.google.common.collect.Lists;
import com.google.protobuf.ByteString;
import com.google.protobuf.InvalidProtocolBufferException;
import io.ray.runtime.serializer.MessagePackSerializer;
import io.ray.serve.common.Constants;
import io.ray.serve.exception.RayServeException;
import io.ray.serve.generated.DeploymentLanguage;
import io.ray.serve.util.MessageFormatter;
import java.io.Serializable;

/** Configuration options for a deployment, to be set by the user. */
public class DeploymentConfig implements Serializable {

  private static final long serialVersionUID = 5965977837248820843L;

  /**
   * The number of processes to start up that will handle requests to this deployment. Defaults to
   * 1.
   */
  private Integer numReplicas = 1;

  /**
   * The maximum number of requests that can be sent to a replica of this deployment without
   * receiving a response. Defaults to 100.
   */
  private Integer maxOngoingRequests = 100;

  /**
   * Arguments to pass to the reconfigure method of the deployment. The reconfigure method is called
   * if user_config is not None.
   */
  private Object userConfig;

  /**
   * Duration that deployment replicas will wait until there is no more work to be done before
   * shutting down.
   */
  private Double gracefulShutdownWaitLoopS = Constants.DEFAULT_GRACEFUL_SHUTDOWN_WAIT_LOOP_S;

  /** Controller waits for this duration to forcefully kill the replica for shutdown. */
  private Double gracefulShutdownTimeoutS = Constants.DEFAULT_GRACEFUL_SHUTDOWN_TIMEOUT_S;

  /** Frequency at which the controller will health check replicas. */
  private Double healthCheckPeriodS = Constants.DEFAULT_HEALTH_CHECK_PERIOD_S;

  /**
   * Timeout that the controller will wait for a response from the replica's health check before
   * marking it unhealthy.
   */
  private Double healthCheckTimeoutS = Constants.DEFAULT_HEALTH_CHECK_TIMEOUT_S;

  private AutoscalingConfig autoscalingConfig;

  private RequestRouterConfig routerConfig;

  /** This flag is used to let replica know they are deplyed from a different language. */
  private Boolean isCrossLanguage = false;

  /** This property tells the controller the deployment's language. */
  private DeploymentLanguage deploymentLanguage = DeploymentLanguage.JAVA;

  private String version;

  private String prevVersion;

  public Integer getNumReplicas() {
    return numReplicas;
  }

  public DeploymentConfig setNumReplicas(Integer numReplicas) {
    if (numReplicas != null) {
      this.numReplicas = numReplicas;
    }
    return this;
  }

  public Integer getMaxOngoingRequests() {
    return maxOngoingRequests;
  }

  public DeploymentConfig setMaxOngoingRequests(Integer maxOngoingRequests) {
    if (maxOngoingRequests != null) {
      Preconditions.checkArgument(maxOngoingRequests > 0, "max_ongoing_requests must be > 0");
      this.maxOngoingRequests = maxOngoingRequests;
    }
    return this;
  }

  public Object getUserConfig() {
    return userConfig;
  }

  public DeploymentConfig setUserConfig(Object userConfig) {
    this.userConfig = userConfig;
    return this;
  }

  public Double getGracefulShutdownWaitLoopS() {
    return gracefulShutdownWaitLoopS;
  }

  public DeploymentConfig setGracefulShutdownWaitLoopS(Double gracefulShutdownWaitLoopS) {
    if (gracefulShutdownWaitLoopS != null) {
      this.gracefulShutdownWaitLoopS = gracefulShutdownWaitLoopS;
    }
    return this;
  }

  public Double getGracefulShutdownTimeoutS() {
    return gracefulShutdownTimeoutS;
  }

  public DeploymentConfig setGracefulShutdownTimeoutS(Double gracefulShutdownTimeoutS) {
    if (gracefulShutdownTimeoutS != null) {
      this.gracefulShutdownTimeoutS = gracefulShutdownTimeoutS;
    }
    return this;
  }

  public Double getHealthCheckPeriodS() {
    return healthCheckPeriodS;
  }

  public DeploymentConfig setHealthCheckPeriodS(Double healthCheckPeriodS) {
    if (healthCheckPeriodS != null) {
      this.healthCheckPeriodS = healthCheckPeriodS;
    }
    return this;
  }

  public Double getHealthCheckTimeoutS() {
    return healthCheckTimeoutS;
  }

  public DeploymentConfig setHealthCheckTimeoutS(Double healthCheckTimeoutS) {
    if (healthCheckTimeoutS != null) {
      this.healthCheckTimeoutS = healthCheckTimeoutS;
    }
    return this;
  }

  public Double getRequestRoutingStatsPeriodS() {
    return routerConfig.getRequestRoutingStatsPeriodS();
  }

  public DeploymentConfig setRequestRoutingStatsPeriodS(Double requestRoutingStatsPeriodS) {
    if (requestRoutingStatsPeriodS != null) {
      routerConfig.setRequestRoutingStatsPeriodS(requestRoutingStatsPeriodS);
    }
    return this;
  }

  public Double getRequestRoutingStatsTimeoutS() {
    return routerConfig.getRequestRoutingStatsTimeoutS();
  }

  public DeploymentConfig setRequestRoutingStatsTimeoutS(Double requestRoutingStatsTimeoutS) {
    if (requestRoutingStatsTimeoutS != null) {
      routerConfig.setRequestRoutingStatsTimeoutS(requestRoutingStatsTimeoutS);
    }
    return this;
  }

  public AutoscalingConfig getAutoscalingConfig() {
    return autoscalingConfig;
  }

  public DeploymentConfig setAutoscalingConfig(AutoscalingConfig autoscalingConfig) {
    this.autoscalingConfig = autoscalingConfig;
    return this;
  }

  public RequestRouterConfig getRequestRouterConfig() {
    return routerConfig;
  }

  public DeploymentConfig setRequestRouterConfig(RequestRouterConfig routerConfig) {
    this.routerConfig = routerConfig;
    return this;
  }

  public boolean isCrossLanguage() {
    return isCrossLanguage;
  }

  public DeploymentConfig setCrossLanguage(Boolean isCrossLanguage) {
    if (isCrossLanguage != null) {
      this.isCrossLanguage = isCrossLanguage;
    }
    return this;
  }

  public DeploymentLanguage getDeploymentLanguage() {
    return deploymentLanguage;
  }

  public DeploymentConfig setDeploymentLanguage(DeploymentLanguage deploymentLanguage) {
    if (deploymentLanguage != null) {
      this.deploymentLanguage = deploymentLanguage;
      this.isCrossLanguage = deploymentLanguage != DeploymentLanguage.JAVA;
    }
    return this;
  }

  public String getVersion() {
    return version;
  }

  public DeploymentConfig setVersion(String version) {
    this.version = version;
    return this;
  }

  public String getPrevVersion() {
    return prevVersion;
  }

  public void setPrevVersion(String prevVersion) {
    this.prevVersion = prevVersion;
  }

  public byte[] toProtoBytes() {
    io.ray.serve.generated.DeploymentConfig.Builder builder =
        io.ray.serve.generated.DeploymentConfig.newBuilder()
            .setNumReplicas(numReplicas)
            .setMaxOngoingRequests(maxOngoingRequests)
            .setMaxQueuedRequests(-1)
            .setGracefulShutdownWaitLoopS(gracefulShutdownWaitLoopS)
            .setGracefulShutdownTimeoutS(gracefulShutdownTimeoutS)
            .setHealthCheckPeriodS(healthCheckPeriodS)
            .setHealthCheckTimeoutS(healthCheckTimeoutS)
            .setIsCrossLanguage(isCrossLanguage)
            .setDeploymentLanguage(deploymentLanguage)
            .setVersion(version);
    if (null != userConfig) {
      builder.setUserConfig(ByteString.copyFrom(MessagePackSerializer.encode(userConfig).getKey()));
    }
    if (null != autoscalingConfig) {
      builder.setAutoscalingConfig(autoscalingConfig.toProto());
    }
    if (null != routerConfig) {
      builder.setRequestRouterConfig(routerConfig.toProto());
    }
    return builder.build().toByteArray();
  }

  public io.ray.serve.generated.DeploymentConfig toProto() {
    io.ray.serve.generated.DeploymentConfig.Builder builder =
        io.ray.serve.generated.DeploymentConfig.newBuilder()
            .setNumReplicas(numReplicas)
            .setMaxOngoingRequests(maxOngoingRequests)
            .setGracefulShutdownWaitLoopS(gracefulShutdownWaitLoopS)
            .setGracefulShutdownTimeoutS(gracefulShutdownTimeoutS)
            .setHealthCheckPeriodS(healthCheckPeriodS)
            .setHealthCheckTimeoutS(healthCheckTimeoutS)
            .setIsCrossLanguage(isCrossLanguage)
            .setDeploymentLanguage(deploymentLanguage);
    if (null != userConfig) {
      builder.setUserConfig(ByteString.copyFrom(MessagePackSerializer.encode(userConfig).getKey()));
    }
    if (null != autoscalingConfig) {
      builder.setAutoscalingConfig(autoscalingConfig.toProto());
    }
    if (null != routerConfig) {
      builder.setRequestRouterConfig(routerConfig.toProto());
    }
    return builder.build();
  }

  public static DeploymentConfig fromProto(io.ray.serve.generated.DeploymentConfig proto) {

    DeploymentConfig deploymentConfig = new DeploymentConfig();
    if (proto == null) {
      return deploymentConfig;
    }
    deploymentConfig.setNumReplicas(proto.getNumReplicas());
    deploymentConfig.setMaxOngoingRequests(proto.getMaxOngoingRequests());
    deploymentConfig.setGracefulShutdownWaitLoopS(proto.getGracefulShutdownWaitLoopS());
    deploymentConfig.setGracefulShutdownTimeoutS(proto.getGracefulShutdownTimeoutS());
    deploymentConfig.setCrossLanguage(proto.getIsCrossLanguage());
    if (proto.getDeploymentLanguage() == DeploymentLanguage.UNRECOGNIZED) {
      throw new RayServeException(
          MessageFormatter.format(
              "Unrecognized deployment language {}. Deployment language must be in {}.",
              proto.getDeploymentLanguage(),
              Lists.newArrayList(DeploymentLanguage.values())));
    }
    deploymentConfig.setDeploymentLanguage(proto.getDeploymentLanguage());
    if (proto.getUserConfig() != null && proto.getUserConfig().size() != 0) {
      deploymentConfig.setUserConfig(
          MessagePackSerializer.decode(
              proto.getUserConfig().toByteArray(), Object.class)); // TODO-xlang
    }
    return deploymentConfig;
  }

  public static DeploymentConfig fromProtoBytes(byte[] bytes) {

    DeploymentConfig deploymentConfig = new DeploymentConfig();
    if (bytes == null) {
      return deploymentConfig;
    }

    io.ray.serve.generated.DeploymentConfig proto = null;
    try {
      proto = io.ray.serve.generated.DeploymentConfig.parseFrom(bytes);
    } catch (InvalidProtocolBufferException e) {
      throw new RayServeException("Failed to parse DeploymentConfig from protobuf bytes.", e);
    }

    return fromProto(proto);
  }
}
