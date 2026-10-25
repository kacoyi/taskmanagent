"""Regression tests for design-checker failures, independent of product implementation."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.check_contracts import DesignError, check_contracts


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = "contracts/architecture.v1.json"
ENGINEERING = "contracts/engineering.v0.json"
EVOLUTION = "contracts/evolution.v1.json"
FIXTURE = "contracts/fixtures/understanding.v1.json"


class ContractCheckerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="taskmanagent-checker-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / "contracts", self.root / "contracts")
        for relative in ("tools/check_contracts.py", "tests/test_contracts.py", "CONTRIBUTING.md",
                         ".github/workflows/design-checks.yml"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

    def edit(self, relative, change):
        path = self.root / relative
        doc = json.loads(path.read_text(encoding="utf-8"))
        change(doc)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def assert_invalid(self, message):
        with self.assertRaises(DesignError) as caught:
            check_contracts(self.root)
        self.assertIn(message, str(caught.exception))

    def test_current_design_is_consistent(self):
        self.assertGreater(check_contracts(self.root)["quality_cases"], 0)

    def test_cycle_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["module_catalog"][0]["allowed_dependencies"].append("understanding"))
        self.assert_invalid("dependency cycle")

    def test_unknown_dependency_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["module_catalog"][0]["allowed_dependencies"].append("missing"))
        self.assert_invalid("unknown dependency")

    def test_duplicate_data_class_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["data_model"]["classes"].append(d["data_model"]["classes"][0]))
        self.assert_invalid("duplicate observed")

    def test_unknown_identity_owner_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["data_model"]["identity_lifecycle"][0].update(owner="missing"))
        self.assert_invalid("unknown data owner")

    def test_malformed_identity_owner_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["data_model"]["identity_lifecycle"][0].update(owner={"invalid": "owner"}))
        self.assert_invalid("expected nonempty text")

    def test_normalized_duplicate_module_path_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["module_catalog"][1].update(planned_path="src/./Foundation"))
        self.assert_invalid("duplicate planned module path")

    def test_dynamic_route_needs_owner_selection(self):
        self.edit(EVOLUTION, lambda d: d["change_routes"][-1].pop("owner_selection"))
        self.assert_invalid("no accountable owner selection")

    def test_unknown_route_scenario_is_rejected(self):
        self.edit(EVOLUTION, lambda d: d["change_routes"][0]["scenarios"].append("S999"))
        self.assert_invalid("unknown or missing scenarios")

    def test_unrouted_scenario_is_rejected(self):
        self.edit(EVOLUTION, lambda d: d["acceptance_scenarios"].append(
            {"id": "S999", "given": "input", "when": "change", "then": "result"}))
        self.assert_invalid("acceptance scenarios without a route")

    def test_unknown_decision_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["decision_refs"].append("ADR-999"))
        self.assert_invalid("unknown decision")

    def test_missing_json_pointer_is_rejected(self):
        self.edit(ENGINEERING, lambda d: d["contract_refs"].update(architecture=ARCHITECTURE + "#/missing"))
        self.assert_invalid("missing JSON pointer target")

    def test_negative_json_pointer_index_is_rejected(self):
        self.edit(ENGINEERING, lambda d: d["contract_refs"].update(architecture=ARCHITECTURE + "#/module_catalog/-1"))
        self.assert_invalid("invalid JSON pointer index")

    def test_json_pointer_escapes_resolve(self):
        self.edit(ARCHITECTURE, lambda d: d.update({"example/key": {"~value": ["ok"]}}))
        self.edit(ENGINEERING, lambda d: d.update(example_ref=ARCHITECTURE + "#/example~1key/~0value/0"))
        check_contracts(self.root)

    def test_reference_cannot_escape_repository(self):
        self.edit(ENGINEERING, lambda d: d["contract_refs"].update(architecture="contracts/../../outside.json"))
        self.assert_invalid("unsafe local path")

    def test_duplicate_json_key_is_rejected(self):
        path = self.root / ENGINEERING
        path.write_text(path.read_text(encoding="utf-8").replace("{", '{"version":"duplicate",', 1), encoding="utf-8")
        self.assert_invalid("duplicate JSON key")

    def test_nan_is_rejected(self):
        self.edit(ENGINEERING, lambda d: d.update(invalid_number=float("nan")))
        self.assert_invalid("non-JSON numeric constant")

    def test_malformed_dependency_list_is_rejected(self):
        self.edit(ARCHITECTURE, lambda d: d["module_catalog"][0].update(allowed_dependencies="understanding"))
        self.assert_invalid("expected a list")

    def test_unknown_acceptance_input_is_rejected(self):
        self.edit(ENGINEERING, lambda d: d["first_delivery_scope"]["acceptance_inputs"].append("invented_permission"))
        self.assert_invalid("unknown acceptance input")

    def test_delivery_requires_success_criteria(self):
        self.edit(ENGINEERING, lambda d: d["first_delivery_scope"].pop("success_checks"))
        self.assert_invalid("first_delivery_scope.success_checks")

    def test_gate_requires_a_check(self):
        self.edit(EVOLUTION, lambda d: d["architecture_gates"][0].pop("check"))
        self.assert_invalid("G01.check")

    def test_removed_stage_gate_is_rejected(self):
        self.edit(EVOLUTION, lambda d: d["architecture_gates"].pop(0))
        self.assert_invalid("unknown gate_refs")

    def test_unknown_stage_scenario_is_rejected(self):
        self.edit(EVOLUTION, lambda d: d["validation_sequence"][1]["scenario_refs"].append("S999"))
        self.assert_invalid("unknown scenario_refs")

    def test_stage_references_cannot_hide_in_prose(self):
        self.edit(EVOLUTION, lambda d: d["validation_sequence"][1].update(exit="G01 exists; S999 passes."))
        self.assert_invalid("use structured gate_refs/scenario_refs")

    def test_product_stage_cannot_omit_gate_references(self):
        self.edit(EVOLUTION, lambda d: d["validation_sequence"][1].update(gate_refs=[]))
        self.assert_invalid("missing gate_refs")

    def test_product_stage_cannot_omit_scenario_references(self):
        self.edit(EVOLUTION, lambda d: d["validation_sequence"][1].pop("scenario_refs"))
        self.assert_invalid("foundation_proof.scenario_refs")

    def test_implemented_gate_needs_evidence(self):
        self.edit(EVOLUTION, lambda d: d["architecture_gates"][0].update(implementation_status="implemented"))
        self.assert_invalid("G01.implementation_evidence_refs")

    def test_implemented_gate_evidence_must_exist(self):
        self.edit(EVOLUTION, lambda d: d["architecture_gates"][0].update(
            implementation_status="implemented", implementation_evidence_refs=["missing-check.py"]))
        self.assert_invalid("missing reference")

    def test_implemented_gate_accepts_existing_evidence(self):
        self.edit(EVOLUTION, lambda d: d["architecture_gates"][-1].update(
            implementation_status="implemented", implementation_evidence_refs=["tools/check_contracts.py"]))
        check_contracts(self.root)  # Path integrity is not a claim that the gate actually ran.

    def test_missing_workflow_guide_is_rejected(self):
        (self.root / "CONTRIBUTING.md").unlink()
        self.assert_invalid("missing reference: CONTRIBUTING.md")

    def test_missing_ci_workflow_is_rejected(self):
        (self.root / ".github/workflows/design-checks.yml").unlink()
        self.assert_invalid("missing reference: .github/workflows/design-checks.yml")

    def test_wrong_evidence_quote_is_rejected(self):
        self.edit(FIXTURE, lambda d: d["evidence"][0].update(quote="from invented import backend"))
        self.assert_invalid("evidence quote differs")

    def test_out_of_range_evidence_is_rejected(self):
        self.edit(FIXTURE, lambda d: d["evidence"][0].update(end_line=999))
        self.assert_invalid("invalid source line range")

    def test_unknown_evidence_reference_is_rejected(self):
        self.edit(FIXTURE, lambda d: d["cases"][0]["expected_claims"][0]["evidence_refs"].append("E999"))
        self.assert_invalid("unknown evidence reference")

    def test_supported_claim_needs_evidence(self):
        self.edit(FIXTURE, lambda d: d["cases"][0]["expected_claims"][0].update(evidence_refs=[]))
        self.assert_invalid("supported claim needs evidence")

    def test_embedded_source_is_never_executed(self):
        self.edit(FIXTURE, lambda d: d["source_files"].update({"unused.py": "raise RuntimeError('must never execute')\n"}))
        check_contracts(self.root)

    def test_cli_fails_with_diagnostic(self):
        self.edit(ARCHITECTURE, lambda d: d["module_catalog"][0]["allowed_dependencies"].append("foundation"))
        result = subprocess.run([sys.executable, str(ROOT / "tools/check_contracts.py"), "--root", str(self.root)],
                                cwd=self.root, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL design consistency", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
