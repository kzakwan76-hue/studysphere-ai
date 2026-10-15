# The TCP three-way handshake

Before two computers exchange data over TCP, they set up a connection with a three-way handshake. The client sends a SYN segment containing an initial sequence number. The server replies with a SYN-ACK segment that acknowledges the client's number and carries its own initial sequence number. The client finishes by sending an ACK segment that acknowledges the server's number. After these three messages the connection is established and data can flow in both directions.

## Why sequence numbers matter

Sequence numbers let each side put arriving bytes back in order and notice missing data. A receiver acknowledges the next byte it expects. If the sender does not receive an acknowledgement within a timeout, it sends the data again.

## Closing a connection

A TCP connection is closed with a FIN segment from each side. One side sends FIN, the other acknowledges it, and then the other side sends its own FIN, which is acknowledged in turn. Because each direction is closed separately, TCP connections can be half-closed.

## TCP compared with UDP

UDP sends independent datagrams without a handshake, acknowledgements or retransmission. It has less delay and overhead, so it suits live video calls and online games where a late packet is worse than a lost one.