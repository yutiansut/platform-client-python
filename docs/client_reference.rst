.. currentmodule:: neuromation.api

Client class
============

.. class:: Client

   Neuromation client.

   For creating a client instance use :class:`Factory` or :func:`get`.

   The class provides access to neuromation subsystems like *jobs* or *storage*.

   .. attribute:: username

      User name used for working with Neuromation platform, read-only :class:`str`.

   .. attribute:: jobs

      Jobs subsystem, see :class:`Jobs` for details.

   .. attribute:: storage

      Storage subsystem, see :class:`Storage` for details.

   .. attribute:: users

      Users subsystem, see :class:`Users` for details.

   .. attribute:: images

      Images subsystem, see :class:`Images` for details.

   .. attribute:: parse

      A set or helpers used for parsing different Neuromation API definitions, see
      :class:`Parser` for details.

   .. comethod:: close()

      Close Neuromation client, all calls after closing are forbidden.

      The method is idempotent.