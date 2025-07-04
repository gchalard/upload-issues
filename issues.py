#! /usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import requests
from typing import Dict, List, Optional

def get_issues(report_path: Path)->List[Dict[str,str]]:
    issues: List[Dict[str,str]] = list()
    with open(report_path, "r") as report:
        issues = json.load(report)
    
    return issues

def get_current_issues(token: str, repo: str, url: str, labels: List[str])->List[Dict[str,str]]:
    issues: List[Dict[str,str]] = list()
    page = 1
    per_page = 100

    labels = ",".join(labels)

    while True:
        try:
            response = requests.get(
                url=f"{url}/repos/{repo}/issues",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                params={
                    "page": page,
                    "per_page": per_page,
                    "labels": labels
                }
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching issues: {e}")
            exit(1)
        else:
            response_data: List[Dict[str,str]] = response.json()
            if not response_data:
                break
            for issue in response_data:
                issue_dict = {
                    "id": issue.get("number"),
                    "title": issue.get("title", ""),
                    "body": issue.get("body", ""),
                    "labels": [label["name"] for label in issue.get("labels", list())]
                }

                issues.append(issue_dict)
        
        finally:
            page += 1
    
    return issues

def _in_(issue: Dict[str,str], issues: List[Dict[str,str]])->bool:
    def _eq_(a:Dict[str,str], b: Dict[str,str])->bool:
        return { "title": a["title"], "body": a["body"], "labels": sorted(a["labels"]) } == { "title": b["title"], "body": b["body"], "labels": sorted(b["labels"]) }
    res = False

    for issue_ in issues:
        if _eq_(issue, issue_):
            return True
        
    return res


def compare_issues(current: List[Dict[str,str]], new: List[Dict[str,str]])->Dict[str,List[Dict[str,str]]]:
    new_issues = [
        issue for issue in new if not _in_(issue=issue, issues=current)
    ]

    issues_to_close = [
        issue for issue in current if not _in_(issue=issue, issues=new)
    ]

    return {
        "new": new_issues,
        "to_close": issues_to_close
    }

def post_issue(issue: Dict[str, str], token: str, repo: str, url: str):
    response = requests.post(
        url=f"{url}/repos/{repo}/issues",
        json=issue,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )

    if response.ok:
        print(f"Issue: {issue['title']} created successfully")
    else:
        print(response.reason)
        print(response.status_code)

def close_issue(issue: Dict[str, str], token: str, repo: str, url: str):
    issue["state"] = "closed"
    issue["labels"].append("resolved")

    try:
        response = requests.patch(
            url=f"{url}/repos/{repo}/issues/{issue['id']}",
            json={
                "state": issue["state"],
                "labels": issue["labels"],
                "title": issue["title"],
                "body": issue["body"]
            },
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )
        
        response.raise_for_status()
    except Exception as e:
        print(f"Error closing issue: {e}")
    else:
        print("Successfully closed the issue")


def main(report_path: Path, token: str, repo: str = None, url: str = None, labels = list())->None:
    potential_issues = get_issues(report_path=report_path)

    labels = labels if not labels == list() else ["nolabels"]
    current_issues = get_current_issues(token=token,repo=repo,url=url,labels=labels)

    issues = compare_issues(current=current_issues, new=potential_issues)

    print(json.dumps(issues, indent=4))

    repo = os.getenv("GITHUB_REPOSITORY") if not repo or repo == "" else repo
    url = os.getenv("GITHUB_API_URL") if not url or url == "" else url

    for issue in issues["to_close"]:
        close_issue(
            issue=issue,
            token=token,
            repo=repo,
            url=url
        )

    for issue in issues["new"]:
        post_issue(
            issue=issue,
            token=token,
            repo=repo,
            url=url
        )

def cli()->None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True, help="The report file well formatted")
    parser.add_argument("--token", required=True, help="The github token")
    parser.add_argument("--repo", required=False, help="The github repo, e.g org/repo")
    parser.add_argument("--api-url", required=False, help="The url of the API")
    parser.add_argument("--labels", required=False, type=lambda labels: labels.split(" "), help="The list of labels to use for comparison, space separated format, e.g 'security sast bandit'")

    args = parser.parse_args()

    print(args.labels)
    main(
        report_path = args.report,
        token=args.token,
        repo=args.repo,
        url=args.api_url,
        labels=args.labels
    )

if __name__ == "__main__":
    cli()