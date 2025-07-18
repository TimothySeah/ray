// Copyright 2017 The Ray Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//  http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

#include <boost/asio/basic_stream_socket.hpp>
#include <boost/asio/buffer.hpp>
#include <boost/asio/error.hpp>
#include <boost/asio/generic/stream_protocol.hpp>
#include <deque>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "ray/common/asio/instrumented_io_context.h"
#include "ray/common/common_protocol.h"
#include "ray/common/id.h"
#include "ray/common/status.h"
#include "ray/raylet/format/node_manager_generated.h"

namespace ray {

using local_stream_protocol = boost::asio::generic::stream_protocol;
using local_stream_socket = boost::asio::basic_stream_socket<local_stream_protocol>;

// Set "close on exec" feature for the given file descriptor.
// WARNING: It does no-op on windows platform.
void SetCloseOnExec(local_stream_socket &socket);
void SetCloseOnExec(boost::asio::basic_socket_acceptor<local_stream_protocol> &acceptor);

/// Connect to a socket with retry times.
Status ConnectSocketRetry(local_stream_socket &socket,
                          const std::string &endpoint,
                          int num_retries = -1,
                          int64_t timeout_in_ms = -1);

/// \typename ServerConnection
///
/// A generic type representing a client connection to a server. This typename
/// can be used to write messages synchronously to the server.
class ServerConnection : public std::enable_shared_from_this<ServerConnection> {
 private:
  // Enables `make_shared` inside of the class without exposing a public constructor.
  struct PrivateTag {};

 public:
  ServerConnection(PrivateTag, local_stream_socket &&socket);
  ServerConnection(const ServerConnection &) = delete;
  ServerConnection &operator=(const ServerConnection &) = delete;

  /// ServerConnection destructor.
  virtual ~ServerConnection();

  /// Allocate a new server connection.
  ///
  /// \param socket A reference to the server socket.
  /// \return std::shared_ptr<ServerConnection>.
  static std::shared_ptr<ServerConnection> Create(local_stream_socket &&socket);

  /// Write a message to the client.
  ///
  /// \param type The message type (e.g., a flatbuffer enum).
  /// \param length The size in bytes of the message.
  /// \param message A pointer to the message buffer.
  /// \return Status.
  ray::Status WriteMessage(int64_t type, int64_t length, const uint8_t *message);

  /// Write a message to the client asynchronously.
  ///
  /// \param type The message type (e.g., a flatbuffer enum).
  /// \param length The size in bytes of the message.
  /// \param message A pointer to the message buffer.
  /// \param handler A callback to run on write completion.
  void WriteMessageAsync(int64_t type,
                         int64_t length,
                         const uint8_t *message,
                         const std::function<void(const ray::Status &)> &handler);

  /// Read a message from the client.
  ///
  /// \param type The message type (e.g., a flatbuffer enum).
  /// \param message A pointer to the message buffer.
  /// \return Status.
  Status ReadMessage(int64_t type, std::vector<uint8_t> *message);

  /// Write a buffer to this connection.
  ///
  /// \param buffer The buffer.
  /// \return Status.
  virtual Status WriteBuffer(const std::vector<boost::asio::const_buffer> &buffer);

  /// Read a buffer from this connection.
  ///
  /// \param buffer The buffer.
  /// \return Status.
  virtual Status ReadBuffer(const std::vector<boost::asio::mutable_buffer> &buffer);

  /// Shuts down socket for this connection.
  void Close() {
    boost::system::error_code ec;
    socket_.close(ec);
  }

  /// Get the native handle of the socket.
  int GetNativeHandle() { return socket_.native_handle(); }

  /// Set the blocking flag of the underlying socket.
  Status SetNonBlocking(bool nonblocking) {
    boost::system::error_code ec;
    socket_.native_non_blocking(nonblocking, ec);
    return boost_to_ray_status(ec);
  }

  std::string DebugString() const;

 protected:
  /// A private constructor for a server connection.
  explicit ServerConnection(local_stream_socket &&socket)
      : ServerConnection(PrivateTag{}, std::move(socket)) {}

  /// A message that is queued for writing asynchronously.
  struct AsyncWriteBuffer {
    int64_t write_cookie;
    int64_t write_type;
    uint64_t write_length;
    std::vector<uint8_t> write_message;
    std::function<void(const ray::Status &)> handler;
  };

  /// The socket connection to the server.
  local_stream_socket socket_;

  /// Max number of messages to write out at once.
  const int async_write_max_messages_;

  /// List of pending messages to write.
  std::deque<std::unique_ptr<AsyncWriteBuffer>> async_write_queue_;

  /// Whether we are in the middle of an async write.
  bool async_write_in_flight_;

  /// Whether we've met a broken-pipe error during writing.
  bool async_write_broken_pipe_;

  /// Count of async messages sent total.
  int64_t async_writes_ = 0;

  /// Count of sync messages sent total.
  int64_t sync_writes_ = 0;

  /// Count of bytes sent total.
  int64_t bytes_written_ = 0;

  /// Count of bytes read total.
  int64_t bytes_read_ = 0;

 private:
  /// Asynchronously flushes the write queue. While async writes are running, the flag
  /// async_write_in_flight_ will be set. This should only be called when no async writes
  /// are currently in flight.
  void DoAsyncWrites();
};

class ClientConnection;

using MessageHandler = std::function<void(
    std::shared_ptr<ClientConnection>, int64_t, const std::vector<uint8_t> &)>;

using ConnectionErrorHandler = std::function<void(std::shared_ptr<ClientConnection>,
                                                  const boost::system::error_code &)>;

/// \typename ClientConnection
///
/// A generic type representing a client connection on a server. In addition to
/// writing messages to the client, like in ServerConnection, this typename can
/// also be used to process messages asynchronously from client.
class ClientConnection : public ServerConnection {
 private:
  // Enables `make_shared` inside of the class without exposing a public constructor.
  struct PrivateTag {};

 public:
  using std::enable_shared_from_this<ServerConnection>::shared_from_this;

  ClientConnection(PrivateTag,
                   MessageHandler message_handler,
                   ConnectionErrorHandler connection_error_handler,
                   local_stream_socket &&socket,
                   std::string debug_label,
                   std::vector<std::string> message_type_enum_names);

  ClientConnection(const ClientConnection &) = delete;
  ClientConnection &operator=(const ClientConnection &) = delete;

  /// Allocate a new node client connection.
  ///
  /// \param message_handler A reference to the message handler.
  /// \param connection_error_handler A reference to the connection error handler.
  /// \param socket The client socket.
  /// \param debug_label Label that is printed in debug messages, to identify
  /// the type of client.
  /// \param message_type_enum_names A table of printable enum names for the
  /// message types received from this client, used for debug messages.
  /// \return std::shared_ptr<ClientConnection>.
  static std::shared_ptr<ClientConnection> Create(
      MessageHandler message_handler,
      ConnectionErrorHandler connection_error_handler,
      local_stream_socket &&socket,
      std::string debug_label,
      std::vector<std::string> message_type_enum_names);

  std::shared_ptr<ClientConnection> shared_ClientConnection_from_this() {
    return std::static_pointer_cast<ClientConnection>(shared_from_this());
  }

  /// Register the client.
  void Register();

  /// Listen for and process messages from the client connection. Once a
  /// message has been fully received, the client manager's
  /// ProcessClientMessage handler will be called.
  void ProcessMessages();

  const std::string GetDebugLabel() const { return debug_label_; }

 protected:
  /// A protected constructor for a node client connection.
  ClientConnection(MessageHandler message_handler,
                   ConnectionErrorHandler connection_error_handler,
                   local_stream_socket &&socket,
                   std::string debug_label,
                   std::vector<std::string> message_type_enum_names)
      : ClientConnection(PrivateTag{},
                         std::move(message_handler),
                         std::move(connection_error_handler),
                         std::move(socket),
                         std::move(debug_label),
                         std::move(message_type_enum_names)) {}
  /// Process an error from the last operation, then process the  message
  /// header from the client.
  void ProcessMessageHeader(const boost::system::error_code &error);
  /// Process an error from reading the message header, then process the
  /// message from the client.
  void ProcessMessage(const boost::system::error_code &error);
  /// Check if the ray cookie in a received message is correct. Note, if the cookie
  /// is wrong and the remote endpoint is known, raylet process will crash. If the remote
  /// endpoint is unknown, this method will only print a warning.
  ///
  /// \return If the cookie is correct.
  bool CheckRayCookie();
  /// Return information about IP and port for the remote endpoint. For local connection
  /// this returns an empty string.
  ///
  /// \return Information of remote endpoint.
  std::string RemoteEndpointInfo();

  /// Whether the client has sent us a registration message yet.
  bool registered_;
  /// The handler for a message from the client.
  MessageHandler message_handler_;
  /// The handler for an unexpected connection error from this client.
  ConnectionErrorHandler connection_error_handler_;
  /// A label used for debug messages.
  const std::string debug_label_;
  /// A table of printable enum names for the message types, used for debug
  /// messages.
  const std::vector<std::string> message_type_enum_names_;
  /// Buffers for the current message being read from the client.
  int64_t read_cookie_;
  int64_t read_type_;
  uint64_t read_length_;
  std::vector<uint8_t> read_message_;
};

// Returns `true` for any connections that have disconnected unexpectedly.
// This functionality is not supported on Windows, so will always return all `false`.
std::vector<bool> CheckForClientDisconnects(
    const std::vector<std::shared_ptr<ClientConnection>> &connections);

}  // namespace ray
