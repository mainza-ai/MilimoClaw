import logging
import os

from milimo_core.stubs.stub_github import StubGitHubClient
from milimo_core.stubs.stub_vercel import StubVercelClient
from milimo_core.stubs.stub_sentry import StubSentryClient
from milimo_core.stubs.stub_stripe import StubStripeClient

logger = logging.getLogger("milimo.service_factory")


def create_github_client(config=None):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPO")
    if token and repo:
        from orchestrator.github_client import GitHubClient

        logger.info("GitHub client: active (GITHUB_TOKEN + GITHUB_REPO)")
        return GitHubClient(repo=repo)
    logger.info("GitHub client: stub (set GITHUB_TOKEN and GITHUB_REPO to activate)")
    return StubGitHubClient()


def create_vercel_client(config=None):
    token = os.environ.get("VERCEL_TOKEN")
    project_id = os.environ.get("VERCEL_PROJECT_ID")
    if token and project_id:
        from orchestrator.build.vercel_client import VercelClient

        logger.info("Vercel client: active (VERCEL_TOKEN + VERCEL_PROJECT_ID)")
        return VercelClient(
            api_token=token,
            project_id=project_id,
            team_id=os.environ.get("VERCEL_TEAM_ID"),
        )
    logger.info(
        "Vercel client: stub (set VERCEL_TOKEN and VERCEL_PROJECT_ID to activate)"
    )
    return StubVercelClient()


def create_sentry_client(config=None):
    token = os.environ.get("SENTRY_AUTH_TOKEN")
    org = os.environ.get("SENTRY_ORG_SLUG")
    project = os.environ.get("SENTRY_PROJECT_SLUG")
    if token and org and project:
        from orchestrator.build.sentry_client import SentryClient

        logger.info(
            "Sentry client: active (SENTRY_AUTH_TOKEN + SENTRY_ORG_SLUG + SENTRY_PROJECT_SLUG)"
        )
        return SentryClient(auth_token=token, org_slug=org, project_slug=project)
    logger.info(
        "Sentry client: stub (set SENTRY_AUTH_TOKEN, SENTRY_ORG_SLUG, SENTRY_PROJECT_SLUG to activate)"
    )
    return StubSentryClient()


def create_stripe_client(config=None):
    api_key = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("STRIPE_API_KEY")
    if api_key:
        from orchestrator.finance.stripe_client import StripeClient

        logger.info("Stripe client: active (STRIPE_SECRET_KEY)")
        return StripeClient(api_key=api_key)
    logger.info("Stripe client: stub (set STRIPE_SECRET_KEY to activate)")
    return StubStripeClient()


def create_railway_client(config=None):
    logger.info("Railway client: stub (not implemented)")
    from orchestrator.stubs.stub_vercel import StubVercelClient

    return StubVercelClient()


def log_active_services():
    services = []
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        services.append("GitHub")
    if os.environ.get("VERCEL_TOKEN"):
        services.append("Vercel")
    if os.environ.get("SENTRY_AUTH_TOKEN"):
        services.append("Sentry")
    if os.environ.get("STRIPE_SECRET_KEY"):
        services.append("Stripe")
    if services:
        logger.info(f"Active external services: {', '.join(services)}")
    else:
        logger.info("No external services configured — running with stubs only")
