"""Invented metadata only: consistency cannot authenticate a source or clock."""

from dataclasses import replace
import unittest

from lab.input_contracts import InputRecord, InputRequirement, check_input_contracts


def snapshot(name="mid", **changes):
    fields = dict(name=name, role="observed", unit="price_quote_per_base",
                  source_sha256="a" * 64, provenance="recorded_receipt",
                  clock_id="invented_common", observation_ns=100,
                  first_seen_ns=110, received_ns=120, available_ns=130,
                  revision_status="none_as_recorded")
    fields.update(changes)
    return InputRecord(**fields)


def requirement(**changes):
    fields = dict(unit="price_quote_per_base", max_age_ns=100)
    fields.update(changes)
    return InputRequirement(**fields)


def check(records, requirements=None, **changes):
    if requirements is None:
        requirements = {record.name: requirement() for record in records}
    fields = dict(decision_ns=200, common_clock_id="invented_common")
    fields.update(changes)
    return check_input_contracts(records, requirements, **fields)


def codes(report, name=None):
    return {i.code for i in report.issues if name is None or i.name == name}


class InputContractTests(unittest.TestCase):
    def test_empty_or_unbounded_graph_is_not_a_consistent_input_receipt(self):
        self.assertIn("empty_inputs", codes(check([], {})))
        rows = [snapshot("x" + str(i)) for i in range(129)]
        self.assertIn("input_limit", codes(check(rows)))
        self.assertIn("invalid_decision_time", codes(check([snapshot()], decision_ns=2**63)))

    def test_consistent_declarations_never_authenticate_or_authorize(self):
        report = check([snapshot()])
        self.assertTrue(report.declaration_checks_passed)
        self.assertEqual(report.input_roles, (("mid", "observed"),))
        for flag in ("source_identity_authenticated", "clock_mapping_verified",
                     "point_in_time_verified", "clock_transform_verified",
                     "historical_availability_proven", "causal_identification_established",
                     "actual_order_allowed", "activation_allowed"):
            self.assertIs(getattr(report, flag), False)
        # CPython raises ValueError through 3.12 and TypeError from 3.13 for a replace() on an
        # init=False field; either way the flag cannot be set.
        with self.assertRaises((ValueError, TypeError)):
            replace(report, actual_order_allowed=True)

    def test_default_age_is_zero_without_an_invented_venue_latency(self):
        report = check([snapshot()], {"mid": InputRequirement("price_quote_per_base")})
        self.assertIn("stale_input", codes(report))
        now = snapshot(observation_ns=200, first_seen_ns=200, received_ns=200,
                       available_ns=200)
        self.assertTrue(check([now], {"mid": InputRequirement(now.unit)}).declaration_checks_passed)

    def test_default_join_skew_is_zero_and_explicit_tolerance_has_a_boundary(self):
        rows = [snapshot("a"), snapshot("b", observation_ns=110)]
        self.assertIn("join_skew", codes(check(rows)))
        self.assertTrue(check(rows, max_join_skew_ns=10).declaration_checks_passed)
        self.assertIn("join_skew", codes(check(rows, max_join_skew_ns=9)))

    def test_a_fresh_download_does_not_refresh_the_observation(self):
        old = snapshot(first_seen_ns=198, received_ns=199, available_ns=200)
        self.assertIn("stale_input", codes(check([old], {"mid": requirement(max_age_ns=20)})))

    def test_matching_receipts_do_not_align_different_observations(self):
        rows = [snapshot("a", received_ns=190, available_ns=200),
                snapshot("b", observation_ns=180, first_seen_ns=190,
                         received_ns=190, available_ns=200)]
        self.assertIn("join_skew", codes(check(rows, max_join_skew_ns=10)))

    def test_publication_requires_its_own_time_and_uses_it_for_age(self):
        release = snapshot(kind="publication", observation_ns=None,
                           publication_ns=100)
        self.assertTrue(check([release]).declaration_checks_passed)
        self.assertIn("missing_publication_time", codes(check([replace(release, publication_ns=None)])))
        self.assertIn("stale_input", codes(check([release], {"mid": requirement(max_age_ns=99)})))

    def test_closed_bar_requires_explicit_boundaries_completion_and_availability(self):
        bar = snapshot(kind="closed_interval", observation_ns=None,
                       interval_start_ns=50, interval_end_ns=100,
                       interval_semantics="start_inclusive_end_exclusive",
                       interval_complete=True)
        self.assertTrue(check([bar]).declaration_checks_passed)
        for changes in (dict(interval_complete=None), dict(interval_complete=1),
                        dict(interval_semantics=None), dict(interval_start_ns=100),
                        dict(interval_end_ns=201)):
            with self.subTest(changes=changes):
                self.assertFalse(check([replace(bar, **changes)]).declaration_checks_passed)
        self.assertIn("before_observation", codes(check([replace(bar, interval_end_ns=150)])))

    def test_revision_status_is_unknown_when_omitted(self):
        record = replace(snapshot(), revision_status="unknown")
        self.assertIn("unknown_revision", codes(check([record])))
        fields = dict(snapshot().__dict__)
        del fields["revision_status"]
        self.assertIn("unknown_revision", codes(check([InputRecord(**fields)])))

    def test_known_revision_requires_time_and_cannot_arrive_in_the_future(self):
        revised = snapshot(revision_status="known", revision_first_seen_ns=115)
        self.assertTrue(check([revised]).declaration_checks_passed)
        self.assertIn("missing_revision_time", codes(check([replace(revised, revision_first_seen_ns=None)])))
        future = replace(revised, revision_first_seen_ns=201)
        self.assertIn("future_timestamp", codes(check([future])))
        self.assertIn("before_revision", codes(check([future])))
        self.assertIn("revision_contradiction", codes(check([replace(revised, revision_status="none_as_recorded")])))

    def test_future_late_and_out_of_order_metadata_is_refused(self):
        self.assertIn("future_timestamp", codes(check([snapshot(available_ns=201)])))
        self.assertIn("availability_order", codes(check([snapshot(received_ns=105)])))
        self.assertIn("before_observation", codes(check([snapshot(first_seen_ns=99)])))

    def test_bool_float_negative_and_missing_timestamps_are_not_cast(self):
        for attr in ("observation_ns", "first_seen_ns", "received_ns", "available_ns",
                     "revision_first_seen_ns", "interval_start_ns", "interval_end_ns", "publication_ns"):
            for invalid in (True, False, 100.0, -1, "100"):
                with self.subTest(attr=attr, invalid=invalid):
                    self.assertIn("invalid_timestamp", codes(check([snapshot(**{attr: invalid})])))
        self.assertIn("invalid_timestamp", codes(check([snapshot(received_ns=None)])))
        self.assertIn("missing_observation_time", codes(check([snapshot(observation_ns=None)])))
        for invalid in (True, 200.0, -1):
            self.assertIn("invalid_decision_time", codes(check([snapshot()], decision_ns=invalid)))

    def test_clock_labels_must_match_but_matching_labels_are_not_proof(self):
        self.assertIn("clock_mismatch", codes(check([snapshot(clock_id="venue_utc")])))
        self.assertIn("invalid_common_clock", codes(check([snapshot()], common_clock_id="")))
        self.assertFalse(check([snapshot()]).clock_mapping_verified)

    def test_unit_labels_distinguish_fractions_percent_and_quantity_conventions(self):
        for required, supplied in (("fraction_per_interval", "percent_per_interval"),
                                   ("quantity_base", "quantity_contracts"),
                                   ("quantity_quote", "quantity_base")):
            self.assertIn("unit_mismatch", codes(check([snapshot(unit=supplied)],
                                                      {"mid": requirement(unit=required)})))

    def test_currency_scale_and_multiplier_are_required_only_by_caller_policy(self):
        record = snapshot()
        self.assertTrue(check([record]).declaration_checks_passed)
        req = requirement(currency="USDT", scale="0.01", multiplier="10")
        failed = check([record], {"mid": req})
        self.assertTrue({"currency_mismatch", "scale_mismatch", "multiplier_mismatch"} <= codes(failed))
        declared = replace(record, currency="USDT", scale="0.0100", multiplier=10)
        self.assertTrue(check([declared], {"mid": req}).declaration_checks_passed)
        self.assertIn("currency_mismatch", codes(check([replace(declared, currency="USDC")], {"mid": req})))
        for invalid in (True, 1.0, "NaN", "Infinity", "0", "-1"):
            self.assertIn("invalid_scale", codes(check([replace(record, scale=invalid)])))

    def test_digest_has_syntax_only_and_does_not_authenticate_identity(self):
        for digest in (None, "", "f" * 63, "z" * 64):
            self.assertIn("invalid_digest", codes(check([snapshot(source_sha256=digest)])))
        report = check([snapshot(source_sha256="0" * 64)])
        self.assertTrue(report.declaration_checks_passed)
        self.assertFalse(report.source_identity_authenticated)

    def test_current_archive_needs_explicit_policy_and_cannot_prove_past_availability(self):
        archive = snapshot(provenance="current_archive")
        self.assertIn("provenance_not_allowed", codes(check([archive])))
        report = check([archive], {"mid": requirement(allowed_provenance=("current_archive",))})
        self.assertTrue(report.declaration_checks_passed)
        self.assertFalse(report.historical_availability_proven)
        self.assertIn("unknown_provenance", codes(check([replace(archive, provenance="unknown")])))

    def test_proxy_allowance_retains_label_and_never_allows_latent_data(self):
        proxy = snapshot(role="proxy")
        self.assertIn("proxy_not_allowed", codes(check([proxy])))
        report = check([proxy], {"mid": requirement(allow_proxy=True)})
        self.assertTrue(report.declaration_checks_passed)
        self.assertEqual(report.input_roles, (("mid", "proxy"),))
        self.assertIn("latent_input", codes(check([replace(proxy, role="latent")],
                                                  {"mid": requirement(allow_proxy=True)})))
        self.assertIn("invalid_role", codes(check([replace(proxy, role="derived")])))

    def test_missing_or_duplicate_inputs_never_supply_zero_or_overwrite(self):
        self.assertIn("missing_input", codes(check([], {"mid": requirement()})))
        self.assertIn("duplicate_input", codes(check([snapshot(), snapshot(role="latent")])))
        self.assertIn("missing_requirement", codes(check([snapshot()], {})))

    def derived(self, **changes):
        return snapshot("derived_mid", kind="derived", observation_ns=None,
                        parents=("mid",), **changes)

    def test_derived_input_requires_parents_and_follows_their_availability(self):
        parent = snapshot()
        child = self.derived(first_seen_ns=140, received_ns=150, available_ns=160)
        self.assertTrue(check([parent, child]).declaration_checks_passed)
        for changes, code in ((dict(parents=()), "missing_parents"),
                              (dict(parents=("missing",)), "missing_parent"),
                              (dict(parents=("mid", "mid")), "duplicate_parent"),
                              (dict(available_ns=129), "before_parent")):
            self.assertIn(code, codes(check([parent, replace(child, **changes)])))

    def test_derived_ancestry_cannot_refresh_old_inputs(self):
        parent = snapshot()
        child = self.derived(first_seen_ns=200, received_ns=200, available_ns=200)
        requirements = {r.name: requirement(max_age_ns=20) for r in (parent, child)}
        report = check([parent, child], requirements)
        self.assertIn("stale_input", codes(report, "mid"))
        self.assertIn("stale_input", codes(report, "derived_mid"))

    def test_derived_construction_cannot_launder_proxy_or_archive_provenance(self):
        parent = snapshot(role="proxy", provenance="current_archive")
        child = self.derived()
        reqs = {r.name: requirement(allow_proxy=True,
                                   allowed_provenance=("recorded_receipt", "current_archive"))
                for r in (parent, child)}
        report = check([parent, child], reqs)
        self.assertIn("role_laundering", codes(report, "derived_mid"))
        self.assertIn("provenance_laundering", codes(report, "derived_mid"))
        child = replace(child, role="proxy", provenance="current_archive")
        report = check([parent, child], reqs)
        self.assertTrue(report.declaration_checks_passed)
        self.assertEqual(dict(report.input_roles)["derived_mid"], "proxy")

    def test_derived_construction_cannot_clear_parent_revision(self):
        parent = snapshot(revision_status="known", revision_first_seen_ns=115)
        child = self.derived()
        self.assertIn("revision_laundering", codes(check([parent, child]), "derived_mid"))
        child = replace(child, revision_status="known", revision_first_seen_ns=115)
        self.assertTrue(check([parent, child]).declaration_checks_passed)
        self.assertIn("before_parent_revision", codes(check([parent, replace(child, revision_first_seen_ns=114)])))

    def test_cycles_and_unconstrained_ancestry_are_refused(self):
        first = snapshot("a", kind="derived", observation_ns=None, parents=("b",))
        second = snapshot("b", kind="derived", observation_ns=None, parents=("a",))
        self.assertIn("dependency_cycle", codes(check([first, second])))
        self.assertIn("missing_requirement", codes(check([snapshot(), self.derived()],
                                                         {"derived_mid": requirement()})))

    def test_invalid_policies_do_not_become_permissive_defaults(self):
        for req in (requirement(max_age_ns=True), requirement(allow_proxy=1),
                    requirement(allowed_provenance=None),
                    requirement(allowed_provenance=("unknown",))):
            self.assertIn("invalid_requirement", codes(check([snapshot()], {"mid": req})))
        for skew in (True, 1.0, -1):
            self.assertIn("invalid_join_tolerance", codes(check([snapshot()], max_join_skew_ns=skew)))


if __name__ == "__main__":
    unittest.main()
