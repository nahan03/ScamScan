"""The single-page checker (FR-1, FR-10). Ad text is analysed in memory and never stored or logged."""

import os

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from scamscan.constants import MAX_CHARS
from scamscan.scorer import analyze, default_classifier


@require_http_methods(["GET", "HEAD", "POST"])
def index(request):
    context = {"max_chars": MAX_CHARS, "text": ""}
    status = 200
    if request.method == "POST":
        text = request.POST.get("ad", "")
        context["text"] = text  # shown again so the user can edit it; not stored anywhere
        try:
            context["result"] = analyze(
                text,
                classifier=default_classifier(),
                use_llm=bool(os.environ.get("ANTHROPIC_API_KEY")),
            )
        except ValueError as error:
            context["error"] = str(error)
            status = 400
    return render(request, "checker/index.html", context, status=status)


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")
