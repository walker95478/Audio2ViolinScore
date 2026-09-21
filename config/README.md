# Configuration

Phase 1A keeps configuration lightweight and dependency-free. Explicit executable overrides are documented in the root `.env.example`; doctor reads the process environment but never loads or writes `.env` automatically.

The future backend configuration belongs here. Do not place secrets, model weights, audio, or generated output in this directory.
