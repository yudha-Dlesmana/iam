from contextvars import ContextVar

actor_id_var: ContextVar[str | None] = ContextVar("audit_actor_id", default=None)
ip_var: ContextVar[str | None] = ContextVar("audit_ip", default=None)
