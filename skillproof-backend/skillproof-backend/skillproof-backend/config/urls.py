from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def health_check(request):
    return HttpResponse("OK", status=200)

def root_view(request):
    html_content = """
    <html>
        <head>
            <title>SkillProof API</title>
            <style>
                body { font-family: -apple-system, system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .card { background: #1e293b; padding: 2rem 4rem; border-radius: 12px; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); border: 1px solid #334155; text-align: center; }
                .status { color: #10b981; font-weight: bold; font-family: monospace; letter-spacing: 2px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🚀 SkillProof Backend</h1>
                <p>The AI Verification Engine is <span class="status">ONLINE AND RUNNING</span></p>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 20px;">API Endpoints are available at /api/</p>
            </div>
        </body>
    </html>
    """
    return HttpResponse(html_content, status=200)

urlpatterns = [
    path('', root_view),
    path('admin/', admin.site.urls),
    path('api/health/', health_check),
    path('api/auth/', include('accounts.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/skills/', include('skills.urls')),
    path('api/assessments/', include('assessments.urls')),
    path('api/badges/', include('badges.urls')),
    path('api/marketplace/', include('marketplace.urls')),
    path('api/network/', include('network.urls')),
    path('api/resumes/', include('resumes.urls')),
    path('api/assistant/', include('assistant.urls')),
    path('api/jobs/', include('jobs.urls')),
    path('api/portfolio/', include('portfolio.urls')),
    path('api/messages/', include('messaging.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
