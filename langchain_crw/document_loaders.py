"""CRW document loader for LangChain.

The implementation lives in the ``crw`` SDK (``crw.integrations.langchain``),
so there is exactly one loader to maintain. This package keeps the conventional
``langchain-<provider>`` name on PyPI and re-exports it.

Security note: Do not pass untrusted user input to ``url``, ``api_url``,
``headers``, or ``proxy`` parameters. These are forwarded as HTTP requests
and could be used for SSRF if exposed to untrusted input.

``CrwClient`` is deliberately not re-exported here. Patching
``langchain_crw.document_loaders.CrwClient`` would no longer affect the loader,
which resolves that name in its own module, so a silent no-op patch is the worst
outcome and an AttributeError is the honest one. Patch
``crw.integrations.langchain.CrwClient`` instead.
"""

from crw.integrations.langchain import CrwLoader

__all__ = ["CrwLoader"]
