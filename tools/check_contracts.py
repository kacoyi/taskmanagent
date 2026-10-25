#!/usr/bin/env python3
"""Validate local design records and fixture integrity, without running product code."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys


class DesignError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DesignError(message)


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ": expected nonempty text")
    return value


def strings(value, label):
    require(isinstance(value, list), label + ": expected a list")
    for item in value:
        nonempty(item, label)
    require(len(value) == len(set(value)), label + ": duplicate entries")
    return value


def records(value, label, key="id"):
    require(isinstance(value, list) and bool(value), label + ": expected nonempty records")
    result = {}
    for item in value:
        require(isinstance(item, dict), label + ": expected an object")
        identity = nonempty(item.get(key), label + "." + key)
        require(identity not in result, label + ": duplicate " + identity)
        result[identity] = item
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise DesignError("non-JSON numeric constant: " + value)


def local_path(root, value):
    path = PurePosixPath(nonempty(value, "local path"))
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in value,
            "unsafe local path: " + value)
    resolved = (root / value).resolve()
    require(resolved.is_relative_to(root), "path escapes repository: " + value)
    return resolved


def resolve_reference(root, docs, reference):
    path, separator, pointer = reference.partition("#")
    target_path = local_path(root, path)
    require(target_path.is_file(), "missing reference: " + reference)
    if not separator:
        return
    require(path in docs, "JSON pointer must target a loaded contract: " + reference)
    require(not pointer or pointer.startswith("/"), "invalid JSON pointer: " + reference)
    target = docs[path]
    for encoded in pointer[1:].split("/") if pointer else []:
        require(re.search(r"~(?![01])", encoded) is None, "invalid JSON pointer escape: " + reference)
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(target, dict):
            require(token in target, "missing JSON pointer target: " + reference)
            target = target[token]
        elif isinstance(target, list):
            require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None,
                    "invalid JSON pointer index: " + reference)
            require(int(token) < len(target), "JSON pointer index out of range: " + reference)
            target = target[int(token)]
        else:
            raise DesignError("JSON pointer traverses a scalar: " + reference)


def walk_references(root, docs, value, scenarios):
    if isinstance(value, dict):
        if "scenario_refs" in value:
            for identity in strings(value["scenario_refs"], "scenario_refs"):
                require(identity in scenarios, "unknown scenario: " + identity)
        for child in value.values():
            walk_references(root, docs, child, scenarios)
    elif isinstance(value, list):
        for child in value:
            walk_references(root, docs, child, scenarios)
    elif isinstance(value, str) and (
            value.startswith(("contracts/", "tools/", "tests/", ".github/"))
            or value in ("AGENTS.md", "CONTRIBUTING.md", "README.md", "SECURITY.md", "LICENSE")):
        resolve_reference(root, docs, value)


def check_fixtures(root, fixture):
    files = fixture.get("source_files")
    require(isinstance(files, dict) and bool(files), "fixture.source_files: expected an object")
    for path, content in files.items():
        local_path(root, path)  # Embedded source is never written or executed.
        nonempty(content, "fixture source " + path)
    evidence = records(fixture.get("evidence"), "fixture.evidence")
    for identity, item in evidence.items():
        path = item.get("path")
        require(isinstance(path, str) and path in files, identity + ": unknown source path")
        start, end = item.get("start_line"), item.get("end_line")
        lines = files[path].splitlines()
        require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines),
                identity + ": invalid source line range")
        require(item.get("quote") == "\n".join(lines[start - 1:end]),
                identity + ": evidence quote differs from source lines")
    cases = records(fixture.get("cases"), "fixture.cases")
    for identity, case in cases.items():
        nonempty(case.get("question"), identity + ".question")
        forbidden = strings(case.get("must_not_claim"), identity + ".must_not_claim")
        require(bool(forbidden), identity + ": missing forbidden conclusions")
        claims = case.get("expected_claims")
        require(isinstance(claims, list) and bool(claims), identity + ": missing expected claims")
        for claim in claims:
            require(isinstance(claim, dict), identity + ": expected a claim object")
            require(claim.get("kind") in ("observation", "inference"), identity + ": invalid claim kind")
            require(claim.get("status") in ("supported", "unknown"), identity + ": invalid claim status")
            nonempty(claim.get("statement"), identity + ".statement")
            nonempty(claim.get("limitations"), identity + ".limitations")
            refs = strings(claim.get("evidence_refs"), identity + ".evidence_refs")
            require(claim["status"] != "supported" or bool(refs), identity + ": supported claim needs evidence")
            require(all(ref in evidence for ref in refs), identity + ": unknown evidence reference")
    return len(cases)


def check_contracts(root):
    root = Path(root).resolve()
    docs, contract_ids = {}, set()
    for path in sorted((root / "contracts").rglob("*.json")):
        relative = path.relative_to(root).as_posix()
        local_path(root, relative)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                             parse_constant=invalid_constant)
        except (ValueError, OSError) as error:
            raise DesignError(relative + ": " + str(error)) from error
        require(isinstance(doc, dict), relative + ": expected a JSON object")
        identity = nonempty(doc.get("contract_id"), relative + ".contract_id")
        require(identity not in contract_ids, "duplicate contract ID: " + identity)
        contract_ids.add(identity)
        require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+-design", str(doc.get("version"))) is not None,
                relative + ": expected an explicit design version")
        docs[relative] = doc
    required = ["engineering.v0", "architecture.v1", "evolution.v1", "decisions.v1"]
    for name in required:
        require("contracts/" + name + ".json" in docs, "missing entry contract: " + name)
    engineering, architecture, evolution, decisions = [docs["contracts/" + name + ".json"] for name in required]
    modules = records(architecture.get("module_catalog"), "module_catalog")
    paths = set()
    for identity, module in modules.items():
        path = nonempty(module.get("planned_path"), identity + ".planned_path")
        planned = local_path(root, path)  # Planned source paths need not exist.
        require(planned not in paths, "duplicate planned module path: " + path)
        paths.add(planned)
        for field in ("owns", "public_contracts", "forbidden_responsibilities"):
            require(bool(strings(module.get(field), identity + "." + field)), identity + ": empty " + field)
        deps = strings(module.get("allowed_dependencies"), identity + ".allowed_dependencies")
        require(all(dep in modules for dep in deps), identity + ": unknown dependency")
    visited, active = set(), []

    def visit(identity):
        require(identity not in active, "dependency cycle: " + " -> ".join(active + [identity]))
        if identity in visited:
            return
        active.append(identity)
        for dep in modules[identity]["allowed_dependencies"]:
            visit(dep)
        active.pop()
        visited.add(identity)

    for identity in modules:
        visit(identity)
    model = architecture.get("data_model")
    require(isinstance(model, dict), "data_model: expected an object")
    for field, key in (("classes", "id"), ("identity_lifecycle", "kind")):
        for item in records(model.get(field), "data_model." + field, key).values():
            owner = nonempty(item.get("owner"), "data_model." + field + ".owner")
            require(owner in modules, "unknown data owner: " + owner)
    adoption = architecture.get("evidence_backed_adoption")
    require(isinstance(adoption, dict), "evidence_backed_adoption: expected an object")
    coordinator = nonempty(adoption.get("coordinator"), "adoption.coordinator")
    require(coordinator in modules, "unknown adoption coordinator")
    owners = adoption.get("record_owners")
    require(isinstance(owners, dict) and bool(owners), "adoption record_owners: expected an object")
    require({"output", "pinned_evidence", "decision"} <= owners.keys(), "missing adoption record owner")
    for owner in owners.values():
        require(nonempty(owner, "adoption record owner") in modules, "unknown adoption record owner")
    require(bool(strings(adoption.get("steps"), "adoption.steps")), "missing adoption steps")
    scenarios = records(evolution.get("acceptance_scenarios"), "acceptance_scenarios")
    for scenario in scenarios.values():
        for field in ("given", "when", "then"):
            nonempty(scenario.get(field), scenario["id"] + "." + field)
    routes = records(evolution.get("change_routes"), "change_routes")
    routed = set()
    for identity, route in routes.items():
        for field in ("owners", "inspect"):
            for owner in strings(route.get(field), identity + "." + field):
                require(owner in modules, identity + ": unknown module " + owner)
        selection = route.get("owner_selection")
        require(bool(route["owners"]) or isinstance(selection, dict), identity + ": no accountable owner selection")
        if selection is not None:
            require(isinstance(selection, dict), identity + ": invalid owner_selection")
            require(selection.get("kind") in ("affected_data_owners", "affected_modules"), identity + ": invalid owner selection kind")
            require(selection.get("catalog_ref") == "contracts/architecture.v1.json#/module_catalog", identity + ": invalid owner catalog")
            nonempty(selection.get("rule"), identity + ".owner_selection.rule")
        for field in ("trigger", "rollback"):
            nonempty(route.get(field), identity + "." + field)
        require(bool(strings(route.get("must_preserve"), identity + ".must_preserve")), identity + ": missing invariants")
        links = strings(route.get("scenarios"), identity + ".scenarios")
        require(bool(links) and all(ref in scenarios for ref in links), identity + ": unknown or missing scenarios")
        routed.update(links)
    require(routed == set(scenarios), "acceptance scenarios without a route: " + ", ".join(sorted(set(scenarios) - routed)))
    adrs = records(decisions.get("decisions"), "decisions")
    for decision in adrs.values():
        for field in ("status", "decision", "reason", "cost", "revisit_when", "reversal"):
            nonempty(decision.get(field), decision["id"] + "." + field)
        require(bool(strings(decision.get("alternatives"), decision["id"] + ".alternatives")), "missing decision alternatives")
    for ref in strings(architecture.get("decision_refs"), "decision_refs"):
        require(ref in adrs, "unknown decision: " + ref)
    gates = records(evolution.get("architecture_gates"), "architecture_gates")
    for gate in gates.values():
        for field in ("name", "required_before", "check"):
            nonempty(gate.get(field), gate["id"] + "." + field)
        require(gate.get("implementation_status") in ("not_implemented", "design_checks_only", "implemented"),
                gate["id"] + ": invalid implementation status")
        if gate["implementation_status"] == "implemented":
            refs = strings(gate.get("implementation_evidence_refs"), gate["id"] + ".implementation_evidence_refs")
            require(bool(refs), gate["id"] + ": missing implementation evidence")
            for ref in refs:
                resolve_reference(root, docs, ref)
    for stage in records(evolution.get("validation_sequence"), "validation_sequence", "stage").values():
        for field in ("deliverable", "exit"):
            value = nonempty(stage.get(field), stage["stage"] + "." + field)
            require(re.search(r"\b[GS][0-9]+\b", value) is None,
                    stage["stage"] + ": use structured gate_refs/scenario_refs, not IDs in prose")
        for field, targets in (("gate_refs", gates), ("scenario_refs", scenarios)):
            refs = strings(stage.get(field), stage["stage"] + "." + field)
            require(all(ref in targets for ref in refs), stage["stage"] + ": unknown " + field)
            require(bool(refs) or stage["stage"] == "architecture_design",
                    stage["stage"] + ": missing " + field)
    delivery = engineering.get("first_delivery_scope")
    require(isinstance(delivery, dict), "first_delivery_scope: expected an object")
    nonempty(delivery.get("outcome"), "first_delivery_scope.outcome")
    for field in ("includes", "deferred", "success_checks", "scenario_refs"):
        require(bool(strings(delivery.get(field), "first_delivery_scope." + field)), "missing first delivery " + field)
    authority = engineering.get("authority")
    require(isinstance(authority, dict) and isinstance(authority.get("unresolved"), dict), "missing product input declarations")
    for name in strings(delivery.get("acceptance_inputs"), "acceptance_inputs"):
        require(name in authority["unresolved"], "unknown acceptance input: " + name)
    for doc in docs.values():
        walk_references(root, docs, doc, scenarios)
    fixture_path = delivery.get("quality_fixture_ref")
    require(isinstance(fixture_path, str) and fixture_path in docs, "missing quality fixture")
    case_count = check_fixtures(root, docs[fixture_path])
    return {"contracts": len(docs), "modules": len(modules), "routes": len(routes),
            "scenarios": len(scenarios), "quality_cases": case_count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        summary = check_contracts(args.root)
    except (DesignError, OSError) as error:
        print("FAIL design consistency: " + str(error), file=sys.stderr)
        return 1
    print("PASS design consistency: " + ", ".join(str(count) + " " + key for key, count in summary.items()))
    print("NOT VERIFIED: product behavior, explanation quality, source dependencies, persistence or authority enforcement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
