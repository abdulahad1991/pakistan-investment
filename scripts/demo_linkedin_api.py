#!/usr/bin/env python3
"""Read-only walkthrough of the Community Management API reads we rely on.

Exists for the LinkedIn Standard Tier access review: their form asks for a
screen recording demonstrating each use case in the request form, and
`post_linkedin.py` only shows the *write* path (Videos + Posts). This script
narrates the read side of the same Page-management use case:

  rw_organization_admin  -> organizationAcls (our admin role), organizations/{id}
  r_organization_social  -> posts?q=author (what the automation has published)

The Page-analytics endpoints (share/page statistics, follower counts) are
behind --with-analytics and stay OFF by default: we only claim Page management
on the access form, and demoing a use case we didn't claim invites questions
we don't need. Turn it on only if the analytics use case is checked.

Nothing here mutates anything. Every call prints the endpoint, the HTTP status
and a short digest of the response, and a failure is reported and skipped
rather than aborting, so a single 403 doesn't kill the recording mid-take.

Env: LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID, LINKEDIN_VERSION (default 202606)
Run: python scripts/demo_linkedin_api.py [--with-analytics]
"""
import json
import os
import sys
from urllib.parse import quote

import requests

REST = "https://api.linkedin.com/rest"


def _hr(title):
    print(f"\n{'=' * 68}\n  {title}\n{'=' * 68}")


def _get(session, label, path, params=None):
    """GET one endpoint, print it the way a reviewer needs to see it."""
    url = f"{REST}{path}"
    print(f"\n[{label}]\n  GET {url}")
    if params:
        print(f"  params {json.dumps(params)}")
    try:
        r = session.get(url, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"  -> request failed: {e}")
        return None
    print(f"  -> HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"  -> {r.text[:400]}")
        return None
    try:
        body = r.json()
    except ValueError:
        print(f"  -> non-JSON body: {r.text[:200]}")
        return None
    print("  -> " + json.dumps(body, indent=2)[:900])
    return body


def main():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    org_id = os.environ.get("LINKEDIN_ORG_ID")
    version = os.environ.get("LINKEDIN_VERSION") or "202606"
    if not (token and org_id):
        print("[demo_linkedin] LINKEDIN_ACCESS_TOKEN / LINKEDIN_ORG_ID not set")
        sys.exit(1)

    org_id = org_id.split(":")[-1]
    owner = f"urn:li:organization:{org_id}"
    encoded_owner = quote(owner, safe="")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
    })

    print(f"pakinvestlysis.com  |  LinkedIn Community Management API demo")
    print(f"organization: {owner}   API version: {version}")

    _hr("PAGE MANAGEMENT 1 - confirm we administer the Page we post to")
    _get(session, "organizationAcls", "/organizationAcls",
         {"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"})

    _hr("PAGE MANAGEMENT 2 - read the Page we publish to")
    _get(session, "organizations", f"/organizations/{org_id}")

    _hr("PAGE MANAGEMENT 3 - list the posts our automation has published")
    _get(session, "posts", "/posts",
         {"q": "author", "author": owner, "count": 5, "sortBy": "LAST_MODIFIED"})

    if "--with-analytics" in sys.argv:
        _hr("PAGE ANALYTICS 1 - lifetime share statistics")
        _get(session, "organizationalEntityShareStatistics",
             "/organizationalEntityShareStatistics",
             {"q": "organizationalEntity", "organizationalEntity": owner})

        _hr("PAGE ANALYTICS 2 - lifetime page views / clicks")
        _get(session, "organizationPageStatistics", "/organizationPageStatistics",
             {"q": "organization", "organization": owner})

        _hr("PAGE ANALYTICS 3 - follower count")
        _get(session, "networkSizes", f"/networkSizes/{encoded_owner}",
             {"edgeType": "CompanyFollowedByMember"})

    print("\nRead-only walkthrough complete. The write path (Videos API upload "
          "-> Posts API publish) runs next via scripts/post_linkedin.py.\n")


if __name__ == "__main__":
    main()
