"""Publish layer — modular multi-platform video distribution.

Each platform is a Publisher (see base.py). The registry exposes which platforms
are configured (have credentials) so the UI/API can offer them. Add a new platform
by dropping a module with a Publisher subclass and registering it in registry.py.
"""
from .base import Publisher, VideoMeta
from . import registry

__all__ = ["Publisher", "VideoMeta", "registry"]
