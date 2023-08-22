# **Checksums** worker for registring distributives in Mongo database basing on *AMQP* queue messages.

## Limitations:

- The primary key for each distributive is a combination of three values: *CITYPE:VERSION:CLIENT*
- Artifact is registered if *CITYPE* ends with `DSTR` only.

## Environment variables:

- **AMQP_URL, AMQP_USER, AMQP_PASSWORD** - for queue connection (*RabbitMQ* or other *AMQP* implementation)
- **MVN_URL, MVN_USER, MVN_PASSWORD** - for maven-like repository connection (*Sontatype Nexus* and *JFrog Artifactory* is currently supported only)
- **DISTRIBUTIVES_API_URL** - URL for *distributives_mongo_api* service (where actual registration is performed).

## Command line arguments:
`--queue` is the only one mandatory since it is not usually set properly by default.
