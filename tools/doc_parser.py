"""Módulo de processamento de documentos de entrada (PDF, DOCX/DOC, Markdown e texto).
- PDFs são mantidos em bytes brutos para consumo multimodal nativo do Gemini; o texto também é
  extraído (MarkItDown) para os caminhos que só leem texto, como a correção de uma missão.
- Documentos DOCX/DOC são convertidos para Markdown estruturado via Microsoft MarkItDown.
- `.md`, `.markdown` e `.txt` entram como estão (UTF-8, com fallback Latin-1).
- Validação estrita: até 60 arquivos e no máximo 25 MB no total.
"""

from dataclasses import dataclass, field
import io
import os
from typing import Any, List, Optional, Tuple

# `markitdown` é importado dentro de `process_document`: ele arrasta o pandas (~320 ms de
# import) e só é necessário quando alguém anexa um .docx — mas era pago em todo start do app.

MAX_FILES: int = 60
MAX_TOTAL_BYTES: int = 25 * 1024 * 1024  # 25 Megabytes
#: Extensões lidas como texto puro, sem conversor.
TEXTO_PURO = {".md": "md", ".markdown": "md", ".txt": "txt"}
EXTENSOES_ACEITAS = ("pdf", "docx", "doc", "md", "markdown", "txt")


@dataclass
class ProcessedDocument:
    """Representação de um documento pronto para consumo pelo modelo."""

    name: str
    file_type: str
    size_bytes: int
    is_native_pdf: bool = False
    pdf_bytes: Optional[bytes] = None
    markdown_text: Optional[str] = None

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


@dataclass
class DocumentBatch:
    """Lote validado de documentos para alimentar o pipeline."""

    documents: List[ProcessedDocument] = field(default_factory=list)
    total_bytes: int = 0

    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)

    @property
    def files_count(self) -> int:
        return len(self.documents)

    @property
    def pdf_count(self) -> int:
        return sum(1 for d in self.documents if d.is_native_pdf)

    @property
    def docx_count(self) -> int:
        return sum(1 for d in self.documents if not d.is_native_pdf)


def process_document(file_name: str, file_bytes: bytes) -> ProcessedDocument:
    """Processa um arquivo conforme o tipo: PDF nativo (+ texto), DOCX via MarkItDown, MD/TXT como texto."""
    ext = os.path.splitext(file_name)[1].lower()
    size_bytes = len(file_bytes)

    if ext == ".pdf":
        return ProcessedDocument(
            name=file_name,
            file_type="pdf",
            size_bytes=size_bytes,
            is_native_pdf=True,
            pdf_bytes=file_bytes,
            # O A004 lê o PDF nativo; quem só lê texto (correção de missão) usa isto.
            markdown_text=_texto_do_pdf(file_name, file_bytes),
        )

    if ext in TEXTO_PURO:
        try:
            texto = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            texto = file_bytes.decode("latin-1")
        return ProcessedDocument(
            name=file_name,
            file_type=TEXTO_PURO[ext],
            size_bytes=size_bytes,
            is_native_pdf=False,
            pdf_bytes=None,
            markdown_text=texto.strip(),
        )

    if ext in (".docx", ".doc"):
        from markitdown import MarkItDown

        md = MarkItDown()
        stream = io.BytesIO(file_bytes)
        try:
            converted = md.convert_stream(stream, file_extension=ext)
            text_content = converted.text_content.strip()
        except Exception as e:
            # Fallback gracioso com aviso
            text_content = f"*(Aviso: Erro ao converter documento Word {file_name}: {str(e)})*"

        return ProcessedDocument(
            name=file_name,
            file_type=ext.replace(".", ""),
            size_bytes=size_bytes,
            is_native_pdf=False,
            pdf_bytes=None,
            markdown_text=text_content,
        )

    raise ValueError(f"Formato de arquivo não suportado: {ext}. Envie PDF, DOCX/DOC, Markdown (.md) ou texto (.txt).")


def _texto_do_pdf(file_name: str, file_bytes: bytes) -> Optional[str]:
    """Texto do PDF via MarkItDown (extra `pdf`). None quando não dá: o PDF nativo continua valendo."""
    if not file_bytes.lstrip().startswith(b"%PDF"):
        # sem cabeçalho de PDF o MarkItDown cai no conversor de texto puro e devolve lixo binário
        return None
    try:
        from markitdown import MarkItDown

        texto = MarkItDown().convert_stream(io.BytesIO(file_bytes), file_extension=".pdf").text_content.strip()
        return texto or None
    except Exception:
        return None


def validate_and_process_batch(uploaded_files: List[Any]) -> Tuple[Optional[DocumentBatch], Optional[str]]:
    """Valida os limites (até 60 arquivos e até 25 MB no total) e processa todos os documentos.

    Args:
        uploaded_files: Lista de objetos de arquivo (ex: UploadedFile do Streamlit).

    Returns:
        Tupla (DocumentBatch, error_message). Se error_message for None, o lote é válido.
    """
    if not uploaded_files:
        return None, None

    if len(uploaded_files) > MAX_FILES:
        return None, f"⚠️ Limite de arquivos excedido: você enviou {len(uploaded_files)} arquivos. O limite máximo é de {MAX_FILES} arquivos."

    total_bytes = 0
    file_tuples = []

    for f in uploaded_files:
        f_name = getattr(f, "name", "documento")
        if hasattr(f, "getvalue"):
            b = f.getvalue()
        elif hasattr(f, "read"):
            b = f.read()
            if hasattr(f, "seek"):
                f.seek(0)
        else:
            b = bytes(f)

        total_bytes += len(b)
        file_tuples.append((f_name, b))

    if total_bytes > MAX_TOTAL_BYTES:
        total_mb = total_bytes / (1024 * 1024)
        return None, f"⚠️ Tamanho total excedido: os documentos somam {total_mb:.2f} MB. O limite máximo é de 25.0 MB."

    batch = DocumentBatch(total_bytes=total_bytes)

    for f_name, f_bytes in file_tuples:
        try:
            doc = process_document(f_name, f_bytes)
            batch.documents.append(doc)
        except Exception as e:
            return None, f"Erro ao processar '{f_name}': {str(e)}"

    return batch, None
