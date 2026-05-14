import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404
from openai import OpenAI
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Notebook, Page, PageUserShare, ShareLink, TopicFolder
from .permissions import IsNotebookOwner, CanAccessPage
from .serializers import (
    NotebookListSerializer,
    NotebookSerializer,
    PageListSerializer,
    PageSerializer,
    PageUserShareSerializer,
    RegisterSerializer,
    SharedPageSerializer,
    SharedWithMeSerializer,
    TopicFolderSerializer,
    UserSerializer,
)


MAX_WEBPAGE_BYTES = 3 * 1024 * 1024
MAX_IMAGE_COUNT = 12
MAX_PARAGRAPH_COUNT = 20
CONTENT_ROOT_TAGS = {"article", "main"}
TEXT_TAGS = {"p", "li", "h1", "h2", "h3", "blockquote"}
SKIP_TAGS = {"script", "style", "nav", "footer", "aside", "noscript", "svg"}
TAG_RE = re.compile(r"<[^>]+>")
META_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?P<key>[^"\']+)["\'][^>]+content=["\'](?P<value>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
DOUBAN_INFO_RE = re.compile(r'<div id="info"[^>]*>(?P<content>.*?)</div>', re.IGNORECASE | re.DOTALL)
DOUBAN_RATING_RE = re.compile(r'property=["\']v:average["\'][^>]*>(?P<value>[^<]+)<', re.IGNORECASE)
DOUBAN_VOTES_RE = re.compile(r'property=["\']v:votes["\'][^>]*>(?P<value>[^<]+)<', re.IGNORECASE)
DOUBAN_TITLE_RE = re.compile(r'property=["\']v:itemreviewed["\'][^>]*>(?P<value>[^<]+)<', re.IGNORECASE)
DOUBAN_SECTION_RE = re.compile(
    r'<h2[^>]*>\s*<span[^>]*>(?P<title>[^<]+)</span>.*?</h2>\s*'
    r'(?:<div[^>]+id="dir_\d+_full"[^>]*>|<div[^>]+class="[^"]*intro[^"]*"[^>]*>)'
    r'(?P<body>.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
BREAK_TAG_RE = re.compile(r"<\s*(br|/p|/div|/li|/tr|/h[1-6])\s*/?>", re.IGNORECASE)


class WebpageExtractor(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.title = ""
        self._in_title = False
        self._capture_text = False
        self._skip_depth = 0
        self._content_root_depth = 0
        self._text_chunks = []
        self.images = []
        self.metadata_lines = []
        self.section_chunks = []

    def add_metadata_line(self, line):
        clean = line.strip()
        if clean and clean not in self.metadata_lines:
            self.metadata_lines.append(clean[:500])

    def add_section_chunk(self, title, body):
        clean_title = title.strip()
        clean_body = body.strip()
        if clean_title and clean_body:
            entry = (clean_title[:120], clean_body[:3000])
            if entry not in self.section_chunks:
                self.section_chunks.append(entry)

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        if tag in CONTENT_ROOT_TAGS:
            self._content_root_depth += 1
        if self._skip_depth == 0 and tag in TEXT_TAGS:
            self._capture_text = True
        if self._skip_depth == 0 and tag == "img":
            src = attrs_dict.get("src")
            if not src:
                return
            parsed = urlparse(src)
            if parsed.scheme not in {"http", "https", ""}:
                return
            if self._content_root_depth == 0:
                class_name = (attrs_dict.get("class") or "").lower()
                alt_text = (attrs_dict.get("alt") or "").strip().lower()
                if any(token in class_name for token in ("logo", "icon", "avatar", "sprite")):
                    return
                if alt_text in {"logo", "icon"}:
                    return
            self.images.append(
                {
                    "src": urljoin(self.base_url, src),
                    "alt": (attrs_dict.get("alt") or "").strip(),
                }
            )

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in TEXT_TAGS:
            self._capture_text = False
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in CONTENT_ROOT_TAGS and self._content_root_depth > 0:
            self._content_root_depth -= 1

    def handle_data(self, data):
        clean = data.strip()
        if not clean:
            return
        if self._in_title:
            self.title = f"{self.title} {clean}".strip()
        elif self._capture_text and self._skip_depth == 0:
            self._text_chunks.append((clean, self._content_root_depth > 0))

    def build_tiptap_doc(self):
        return self.build_basic_tiptap_doc()

    def get_content_chunks(self):
        preferred_chunks = [chunk for chunk, is_preferred in self._text_chunks if is_preferred]
        fallback_chunks = [chunk for chunk, is_preferred in self._text_chunks if not is_preferred]
        combined = preferred_chunks or fallback_chunks
        for title, body in self.section_chunks:
            combined.append(f"{title}\n{body}")
        return combined

    def get_plain_text(self):
        parts = []
        if self.metadata_lines:
            parts.append("Metadata:\n" + "\n".join(self.metadata_lines[:20]))
        parts.extend(self.get_content_chunks()[:MAX_PARAGRAPH_COUNT])
        return "\n\n".join(parts).strip()

    def get_image_nodes(self):
        seen = set()
        image_nodes = []
        for image in self.images:
            if image["src"] in seen:
                continue
            seen.add(image["src"])
            image_nodes.append(
                {
                    "type": "image",
                    "attrs": {"src": image["src"], "alt": image["alt"], "title": ""},
                }
            )
            if len(image_nodes) >= MAX_IMAGE_COUNT:
                break
        return image_nodes

    def build_basic_tiptap_doc(self, title_override=None):
        nodes = []
        heading_title = (title_override or self.title).strip()
        if heading_title:
            nodes.append(
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": heading_title[:300]}],
                }
            )

        content_chunks = self.get_content_chunks()

        nodes.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": f"Source: {self.base_url}"}],
            }
        )

        if self.metadata_lines:
            nodes.append(
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Details"}],
                }
            )
            nodes.append(
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": line}],
                                }
                            ],
                        }
                        for line in self.metadata_lines[:20]
                    ],
                }
            )

        for chunk in content_chunks[:MAX_PARAGRAPH_COUNT]:
            nodes.append(
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": chunk[:2000]}],
                }
            )

        image_nodes = self.get_image_nodes()
        if image_nodes:
            nodes.append(
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Images"}],
                }
            )
            nodes.extend(image_nodes)

        if not nodes:
            nodes.append(
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "No readable content extracted from webpage."}],
                }
            )

        return {"type": "doc", "content": nodes}

    def enrich_from_html(self, html_text):
        for match in META_RE.finditer(html_text):
            key = match.group("key").strip().lower()
            value = clean_html_fragment(match.group("value"))
            if not value:
                continue
            if key in {"description", "og:description"}:
                self.add_section_chunk("Description", value)
            elif key in {"keywords"}:
                self.add_metadata_line(f"Keywords: {value}")

        parsed_url = urlparse(self.base_url)
        if parsed_url.netloc == "book.douban.com":
            self._enrich_douban_book_page(html_text)

    def _enrich_douban_book_page(self, html_text):
        title_match = DOUBAN_TITLE_RE.search(html_text)
        if title_match:
            self.title = clean_html_fragment(title_match.group("value")) or self.title

        info_match = DOUBAN_INFO_RE.search(html_text)
        if info_match:
            for line in split_html_lines(info_match.group("content")):
                self.add_metadata_line(line)

        rating_match = DOUBAN_RATING_RE.search(html_text)
        votes_match = DOUBAN_VOTES_RE.search(html_text)
        if rating_match:
            rating = clean_html_fragment(rating_match.group("value"))
            votes = clean_html_fragment(votes_match.group("value")) if votes_match else ""
            suffix = f" ({votes} ratings)" if votes else ""
            self.add_metadata_line(f"Douban rating: {rating}{suffix}")

        for match in DOUBAN_SECTION_RE.finditer(html_text):
            title = clean_html_fragment(match.group("title"))
            body = clean_html_fragment(match.group("body"), preserve_breaks=True)
            if title and body:
                self.add_section_chunk(title, body)


def clean_html_fragment(fragment, preserve_breaks=False):
    text = fragment
    if preserve_breaks:
        text = BREAK_TAG_RE.sub("\n", text)
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines) if preserve_breaks else " ".join(lines)


def split_html_lines(fragment):
    text = clean_html_fragment(fragment, preserve_breaks=True)
    return [line for line in text.splitlines() if line.strip()]


def fetch_webpage(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://")

    request = Request(
        url,
        headers={
            "User-Agent": "GreatNotesBot/1.0 (+https://greatnotes.local)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type:
                raise ValueError("Only HTML webpages are supported.")
            raw = response.read(MAX_WEBPAGE_BYTES + 1)
    except HTTPError as exc:
        raise ValueError(f"Webpage returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ValueError(f"Failed to fetch webpage: {exc.reason}") from exc

    if len(raw) > MAX_WEBPAGE_BYTES:
        raise ValueError("Webpage is too large.")

    parser = WebpageExtractor(url)
    html_text = raw.decode("utf-8", errors="replace")
    parser.feed(html_text)
    parser.close()
    parser.enrich_from_html(html_text)
    return parser


def build_openai_models():
    models = []
    for model_name in (settings.OPENAI_MODEL, "gpt-5.3-codex", "gpt-4o-mini"):
        if model_name and model_name not in models:
            models.append(model_name)
    return models


def extract_json_object(text):
    if not text:
        raise ValueError("Empty AI response")
    content = text.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(content[start : end + 1])


def build_ai_import_doc(source_url, title_text, summary_text, key_points, body_paragraphs, image_nodes, import_mode_text):
    nodes = []
    if title_text:
        nodes.append(
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": title_text[:300]}],
            }
        )

    nodes.append(
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": f"Source: {source_url}"}],
        }
    )
    nodes.append(
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": import_mode_text}],
        }
    )

    if summary_text:
        nodes.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Summary"}],
            }
        )
        nodes.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": summary_text[:2000]}],
            }
        )

    cleaned_points = [point.strip() for point in key_points if isinstance(point, str) and point.strip()]
    if cleaned_points:
        nodes.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Key Points"}],
            }
        )
        nodes.append(
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": point[:500]}],
                            }
                        ],
                    }
                    for point in cleaned_points[:8]
                ],
            }
        )

    cleaned_body = [paragraph.strip() for paragraph in body_paragraphs if isinstance(paragraph, str) and paragraph.strip()]
    if cleaned_body:
        nodes.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Notes"}],
            }
        )
        for paragraph in cleaned_body[:12]:
            nodes.append(
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": paragraph[:2000]}],
                }
            )

    if image_nodes:
        nodes.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Images"}],
            }
        )
        nodes.extend(image_nodes)

    return {"type": "doc", "content": nodes}


def organize_webpage_with_ai(parsed, explicit_title=""):
    fallback_title = (explicit_title or parsed.title or f"Imported: {urlparse(parsed.base_url).netloc}")[:255]
    fallback_doc = parsed.build_basic_tiptap_doc(title_override=fallback_title)
    if not settings.OPENAI_API_KEY:
        fallback_doc["content"].insert(
            2,
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Import mode: Basic fallback (AI not configured)"}],
            },
        )
        return fallback_title, fallback_doc, "fallback", "AI not configured"

    source_text = parsed.get_plain_text()
    if not source_text:
        fallback_doc["content"].insert(
            2,
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Import mode: Basic fallback (no readable text extracted)"}],
            },
        )
        return fallback_title, fallback_doc, "fallback", "No readable text extracted"

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL or None)
    prompt = (
        "You convert webpage text into clean study notes. "
        "Return valid JSON only with keys: title, summary, key_points, body. "
        "title must be a short string. "
        "summary must be 1-2 sentences. "
        "key_points must be an array of concise bullet strings. "
        "body must be an array of paragraph strings. "
        "Do not include markdown fences or extra commentary."
    )
    user_content = (
        f"Source URL: {parsed.base_url}\n"
        f"Original title: {parsed.title or 'Untitled'}\n"
        f"Preferred notebook title: {explicit_title or 'None'}\n\n"
        f"Extracted webpage text:\n{source_text[:12000]}"
    )

    last_error = None
    for model_name in build_openai_models():
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )
            payload = extract_json_object(response.choices[0].message.content)
            ai_title = str(payload.get("title") or "").strip() or fallback_title
            page_title = (explicit_title or ai_title or fallback_title)[:255]
            summary_text = str(payload.get("summary") or "").strip()
            key_points = payload.get("key_points") or []
            body_paragraphs = payload.get("body") or []
            doc = build_ai_import_doc(
                parsed.base_url,
                page_title,
                summary_text,
                key_points,
                body_paragraphs,
                parsed.get_image_nodes(),
                f"Import mode: AI organized ({model_name})",
            )
            return page_title, doc, "ai", model_name
        except Exception as exc:
            last_error = exc
            continue

    detail = f"AI import failed: {last_error}" if last_error else "AI import failed"
    fallback_doc["content"].insert(
        2,
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": f"Import mode: Basic fallback ({detail[:180]})"}],
        },
    )
    return fallback_title, fallback_doc, "fallback", detail


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class NotebookListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["title", "pages__title"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return NotebookListSerializer
        return NotebookSerializer

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotebookDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NotebookSerializer
    permission_classes = [IsAuthenticated, IsNotebookOwner]

    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)


class TopicFolderListCreateView(generics.ListCreateAPIView):
    serializer_class = TopicFolderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        notebook_id = self.request.query_params.get("notebook")
        queryset = TopicFolder.objects.filter(notebook__user=self.request.user)
        if notebook_id:
            queryset = queryset.filter(notebook_id=notebook_id)
        return queryset


class TopicFolderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TopicFolderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TopicFolder.objects.filter(notebook__user=self.request.user)


class PageListCreateView(generics.ListCreateAPIView):
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["notebook_id"] = int(self.kwargs["notebook_pk"])
        return context

    def get_queryset(self):
        notebook = get_object_or_404(Notebook, pk=self.kwargs["notebook_pk"], user=self.request.user)
        queryset = notebook.pages.all()
        folder_id = self.request.query_params.get("topic_folder")
        if folder_id:
            if folder_id == "null":
                queryset = queryset.filter(topic_folder__isnull=True)
            else:
                queryset = queryset.filter(topic_folder_id=folder_id, topic_folder__notebook=notebook)
        return queryset

    def perform_create(self, serializer):
        notebook = get_object_or_404(Notebook, pk=self.kwargs["notebook_pk"], user=self.request.user)
        serializer.save(notebook=notebook, order=notebook.pages.count())


class PageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated, CanAccessPage]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        page = self.get_object()
        context["notebook_id"] = page.notebook_id
        return context

    def get_queryset(self):
        return Page.objects.filter(
            models.Q(notebook__user=self.request.user)
            | models.Q(user_shares__user=self.request.user)
        ).distinct()


class FavoritePageListView(generics.ListAPIView):
    serializer_class = PageListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Page.objects.filter(notebook__user=self.request.user, is_favorite=True).order_by("-updated_at")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_webpage(request, notebook_pk):
    notebook = get_object_or_404(Notebook, pk=notebook_pk, user=request.user)
    url = (request.data.get("url") or "").strip()
    title = (request.data.get("title") or "").strip()
    topic_folder_id = request.data.get("topic_folder")

    if not url:
        return Response({"detail": "url is required"}, status=status.HTTP_400_BAD_REQUEST)

    folder = None
    if topic_folder_id is not None and str(topic_folder_id).lower() not in {"", "null"}:
        folder = get_object_or_404(TopicFolder, pk=topic_folder_id, notebook=notebook)

    try:
        parsed = fetch_webpage(url)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    page_title, page_content, import_mode, import_detail = organize_webpage_with_ai(parsed, title)

    page = Page.objects.create(
        notebook=notebook,
        title=page_title,
        content=page_content,
        order=notebook.pages.count(),
        topic_folder=folder,
    )
    serializer = PageSerializer(page, context={"request": request, "notebook_id": notebook.id})
    return Response(
        {
            **serializer.data,
            "import_mode": import_mode,
            "import_detail": import_detail,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def page_share(request, pk):
    page = get_object_or_404(Page, pk=pk, notebook__user=request.user)

    if request.method == "POST":
        link, _ = ShareLink.objects.get_or_create(page=page, is_active=True)
        return Response({"token": str(link.token)}, status=status.HTTP_200_OK)

    ShareLink.objects.filter(page=page, is_active=True).update(is_active=False)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def page_share_users(request, pk):
    page = get_object_or_404(Page, pk=pk, notebook__user=request.user)

    if request.method == "GET":
        shares = page.user_shares.select_related("user").all()
        serializer = PageUserShareSerializer(shares, many=True)
        return Response(serializer.data)

    username = request.data.get("username")
    if not username:
        return Response({"detail": "username is required"}, status=status.HTTP_400_BAD_REQUEST)

    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        return Response({"detail": "Cannot share with yourself"}, status=status.HTTP_400_BAD_REQUEST)

    share, created = PageUserShare.objects.get_or_create(page=page, user=target_user)
    serializer = PageUserShareSerializer(share)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def page_share_user_revoke(request, pk, user_id):
    page = get_object_or_404(Page, pk=pk, notebook__user=request.user)
    share = get_object_or_404(PageUserShare, page=page, user_id=user_id)
    share.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shared_with_me(request):
    pages = Page.objects.filter(user_shares__user=request.user).distinct()
    serializer = SharedWithMeSerializer(pages, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def shared_page(request, token):
    link = get_object_or_404(ShareLink, token=token, is_active=True)
    serializer = SharedPageSerializer(link.page)
    return Response(serializer.data)


AI_EDIT_PROMPTS = {
    "improve": "Improve the writing quality of the following text. Keep the meaning and tone. Return only the improved text, no explanations.",
    "shorter": "Make the following text shorter and more concise. Preserve the key meaning. Return only the shortened text, no explanations.",
    "longer": "Expand the following text with more detail and depth. Keep the same style. Return only the expanded text, no explanations.",
    "grammar": "Fix grammar and spelling in the following text. Do not change the meaning or style. Return only the corrected text, no explanations.",
    "professional": "Rewrite the following text in a professional, formal tone. Return only the rewritten text, no explanations.",
    "casual": "Rewrite the following text in a casual, conversational tone. Return only the rewritten text, no explanations.",
}


def build_ai_edit_models():
    return build_openai_models()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_edit(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if page.notebook.user != request.user and not page.user_shares.filter(user=request.user).exists():
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    text = request.data.get("text", "").strip()
    action = request.data.get("action", "").strip()
    if not text:
        return Response({"detail": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
    if action not in AI_EDIT_PROMPTS:
        return Response(
            {"detail": f"action must be one of: {', '.join(AI_EDIT_PROMPTS.keys())}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not settings.OPENAI_API_KEY:
        return Response({"detail": "AI editing is not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL or None)
    last_error = None
    for model_name in build_ai_edit_models():
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": AI_EDIT_PROMPTS[action]},
                    {"role": "user", "content": text},
                ],
                temperature=0.7,
            )
            transformed = response.choices[0].message.content.strip()
            return Response({"text": transformed, "model": model_name})
        except Exception as exc:
            last_error = exc

    detail = "AI transformation failed"
    if settings.DEBUG and last_error:
        detail = f"{detail}: {last_error}"
    return Response({"detail": detail}, status=status.HTTP_502_BAD_GATEWAY)
