"""Smoke tests for the safety classifier in bin/porkbun-api-skill.

Run with:
    python3 -m unittest discover tests

These tests are deliberately offline and stdlib-only — they load
bin/porkbun-api-skill via importlib.machinery.SourceFileLoader and exercise
the classifier and helpers directly. No network, no credentials required.
"""

from __future__ import annotations

import importlib.machinery
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LOADER = importlib.machinery.SourceFileLoader(
    "porkbun_ctl", str(REPO_ROOT / "bin" / "porkbun-api-skill")
)
pb = LOADER.load_module()


class TestNormalizePath(unittest.TestCase):
    def test_known_template_with_numeric_id(self):
        self.assertEqual(
            pb._normalize_path("/dns/delete/example.com/12345"),
            "/dns/delete/{domain}/{id}",
        )

    def test_known_template_with_subdomain_pattern(self):
        self.assertEqual(
            pb._normalize_path("/dns/deleteByNameType/example.com/A/www"),
            "/dns/deleteByNameType/{domain}/{type}/{subdomain}",
        )

    def test_known_template_domain_only(self):
        self.assertEqual(
            pb._normalize_path("/domain/get/example.com"),
            "/domain/get/example.com",  # /domain/get/{domain} not in classifier table; passes through
        )
        # /domain/create/{domain} IS in the table though.
        self.assertEqual(
            pb._normalize_path("/domain/create/example.com"),
            "/domain/create/{domain}",
        )

    def test_unknown_path_passes_through(self):
        self.assertEqual(
            pb._normalize_path("/some/future/endpoint"),
            "/some/future/endpoint",
        )

    def test_strips_v3_prefix(self):
        self.assertEqual(
            pb._normalize_path("/v3/domain/create/example.com"),
            "/domain/create/{domain}",
        )
        self.assertEqual(
            pb._normalize_path("/api/json/v3/dns/delete/example.com/12345"),
            "/dns/delete/{domain}/{id}",
        )

    def test_does_not_strip_unrelated_prefix(self):
        self.assertEqual(
            pb._normalize_path("/v30/foo"),
            "/v30/foo",
        )


class TestClassify(unittest.TestCase):
    def test_get_is_read(self):
        cls, flags, _why = pb.classify("GET", "/domain/listAll")
        self.assertEqual(cls, "read")
        self.assertEqual(flags, [])

    def test_get_balance_is_read(self):
        cls, flags, _why = pb.classify("GET", "/account/balance")
        self.assertEqual(cls, "read")
        self.assertEqual(flags, [])

    def test_post_ping_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/ping")
        self.assertEqual(cls, "read")

    def test_post_check_domain_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/domain/checkDomain/example.com")
        self.assertEqual(cls, "read")

    def test_post_pricing_get_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/pricing/get")
        self.assertEqual(cls, "read")

    def test_post_listall_is_read(self):
        cls, _flags, _why = pb.classify("POST", "/domain/listAll")
        self.assertEqual(cls, "read")

    def test_post_dns_create_is_mutating(self):
        cls, flags, _why = pb.classify("POST", "/dns/create/example.com")
        self.assertEqual(cls, "mutating")
        self.assertEqual(flags, ["--yes"])

    def test_post_dns_edit_is_mutating(self):
        cls, _flags, _why = pb.classify("POST", "/dns/edit/example.com/12345")
        self.assertEqual(cls, "mutating")

    def test_post_update_ns_is_mutating(self):
        cls, _flags, _why = pb.classify("POST", "/domain/updateNs/example.com")
        self.assertEqual(cls, "mutating")

    def test_post_dns_delete_is_destructive(self):
        cls, flags, _why = pb.classify("POST", "/dns/delete/example.com/12345")
        self.assertEqual(cls, "destructive")
        self.assertIn("--confirm-id", flags)

    def test_post_dns_delete_by_nametype_uses_confirm_name(self):
        # Pattern-deletes (delete-by-subdomain) need --confirm-name, not --confirm-id.
        cls, flags, _why = pb.classify(
            "POST", "/dns/deleteByNameType/example.com/A/www"
        )
        self.assertEqual(cls, "destructive")
        self.assertIn("--confirm-name", flags)
        self.assertNotIn("--confirm-id", flags)

    def test_post_delete_glue_is_destructive(self):
        cls, _flags, _why = pb.classify(
            "POST", "/domain/deleteGlue/example.com/ns1"
        )
        self.assertEqual(cls, "destructive")

    def test_post_delete_url_forward_is_destructive(self):
        cls, _flags, _why = pb.classify(
            "POST", "/domain/deleteUrlForward/example.com/77"
        )
        self.assertEqual(cls, "destructive")

    def test_post_create_domain_is_billable(self):
        cls, flags, _why = pb.classify("POST", "/domain/create/example.com")
        self.assertEqual(cls, "billable")
        self.assertIn("--i-understand-billing", flags)

    def test_post_renew_domain_is_billable(self):
        cls, _flags, _why = pb.classify("POST", "/domain/renew/example.com")
        self.assertEqual(cls, "billable")

    def test_post_transfer_domain_is_billable(self):
        cls, _flags, _why = pb.classify("POST", "/domain/transfer/example.com")
        self.assertEqual(cls, "billable")

    def test_post_apikey_request_is_privilege(self):
        cls, flags, _why = pb.classify("POST", "/apikey/request")
        self.assertEqual(cls, "privilege")
        self.assertIn("--allow-privilege", flags)

    def test_post_apikey_retrieve_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/apikey/retrieve")
        self.assertEqual(cls, "privilege")

    def test_post_account_invite_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/account/invite")
        self.assertEqual(cls, "privilege")

    def test_post_email_setpassword_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/email/setPassword")
        self.assertEqual(cls, "privilege")

    def test_get_ssl_retrieve_is_privilege(self):
        # SSL retrieve returns private key material — privilege regardless of method.
        cls, flags, _why = pb.classify("GET", "/ssl/retrieve/example.com")
        self.assertEqual(cls, "privilege")
        self.assertIn("--allow-privilege", flags)

    def test_post_ssl_retrieve_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/ssl/retrieve/example.com")
        self.assertEqual(cls, "privilege")

    def test_unknown_post_defaults_to_mutating(self):
        # POST-to-delete-without-being-in-the-table must NOT default to destructive;
        # the explicit table is the only source of `destructive`. We accept that an
        # unknown POST falls through to `mutating` (requires --yes) and rely on the
        # operator to recognize a delete-style path. This is the same approach as
        # linode-api-skill but more conservative on the destructive tier.
        cls, flags, _why = pb.classify("POST", "/future/endpoint")
        self.assertEqual(cls, "mutating")
        self.assertEqual(flags, ["--yes"])

    def test_method_case_insensitive(self):
        cls_lower, _, _ = pb.classify("post", "/domain/listAll")
        cls_upper, _, _ = pb.classify("POST", "/domain/listAll")
        self.assertEqual(cls_lower, cls_upper)

    def test_v3_prefix_create_is_billable(self):
        cls, flags, _why = pb.classify("POST", "/v3/domain/create/example.com")
        self.assertEqual(cls, "billable")
        self.assertIn("--i-understand-billing", flags)

    def test_v3_prefix_apikey_is_privilege(self):
        cls, _flags, _why = pb.classify("POST", "/v3/apikey/request")
        self.assertEqual(cls, "privilege")

    def test_full_api_prefix_strips(self):
        cls, _flags, _why = pb.classify(
            "POST", "/api/json/v3/dns/delete/example.com/12345"
        )
        self.assertEqual(cls, "destructive")


class TestPathValidation(unittest.TestCase):
    def test_rejects_traversal_dotdot(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_path("/../../etc/passwd")

    def test_rejects_traversal_dot(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_path("/./dns/retrieve/example.com")

    def test_rejects_url_encoded_percent(self):
        with self.assertRaises(pb.CtlError):
            pb._validate_path("/dns/retrieve/%2e%2e/etc")

    def test_rejects_unsupported_chars(self):
        for bad in ["/foo?x=1", "/foo#frag", "/foo bar", "/foo\\bar"]:
            with self.subTest(path=bad), self.assertRaises(pb.CtlError):
                pb._validate_path(bad)

    def test_accepts_normal_paths(self):
        for good in [
            "/ping",
            "/domain/listAll",
            "/dns/retrieve/example.com",
            "/dns/delete/example.com/12345",
            "/domain/create/example.com",
            "/dns/deleteByNameType/example.com/A/www",
        ]:
            with self.subTest(path=good):
                pb._validate_path(good)  # should not raise


class TestDomainValidation(unittest.TestCase):
    def test_accepts_normal_domains(self):
        for good in ["example.com", "foo.io", "sub.example.co.uk", "xn--abc.com",
                     "ns1.porkbun.com"]:
            with self.subTest(domain=good):
                pb._validate_domain(good)

    def test_rejects_garbage(self):
        for bad in ["", "no-tld", "..", "example..com", "-leading.com",
                    "trailing-.com", "with space.com", "with/slash.com"]:
            with self.subTest(domain=bad), self.assertRaises(pb.CtlError):
                pb._validate_domain(bad)


class TestPriceParsing(unittest.TestCase):
    def test_dollars_and_cents(self):
        self.assertEqual(pb._parse_price_to_cents("9.73"), 973)
        self.assertEqual(pb._parse_price_to_cents("12.00"), 1200)
        self.assertEqual(pb._parse_price_to_cents("0.99"), 99)

    def test_whole_dollars(self):
        self.assertEqual(pb._parse_price_to_cents("12"), 1200)

    def test_one_decimal(self):
        # "9.7" should be 970 cents (interpreted as $9.70).
        self.assertEqual(pb._parse_price_to_cents("9.7"), 970)

    def test_strips_dollar_sign(self):
        self.assertEqual(pb._parse_price_to_cents("$9.73"), 973)

    def test_rejects_garbage(self):
        for bad in ["", "not-a-price", "9.999", "9.7.3", "-1.00"]:
            with self.subTest(price=bad), self.assertRaises(pb.CtlError):
                pb._parse_price_to_cents(bad)


class TestPlatformHelpers(unittest.TestCase):
    def test_no_gui_error_returns_ctlerror(self):
        err = pb._no_gui_error()
        self.assertIsInstance(err, pb.CtlError)

    def test_has_display_returns_bool(self):
        self.assertIsInstance(pb._has_display(), bool)

    def test_platform_known(self):
        self.assertIn(pb._platform(), {"macos", "linux", "windows", "unknown"})


class TestPackUnpack(unittest.TestCase):
    def test_pack_unpack_roundtrip(self):
        blob = pb._pack("pk1_AAA", "sk1_BBB")
        self.assertEqual(pb._unpack(blob), ("pk1_AAA", "sk1_BBB"))

    def test_unpack_missing_field_returns_none(self):
        self.assertIsNone(pb._unpack('{"apikey": "only-one"}'))
        self.assertIsNone(pb._unpack("not-json"))
        self.assertIsNone(pb._unpack('{"apikey": "", "secretapikey": ""}'))


class TestCliEntrypoint(unittest.TestCase):
    def test_version_flag_exits_zero(self):
        # argparse's --version calls SystemExit(0) — catch it.
        with self.assertRaises(SystemExit) as cm:
            pb.main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_classify_command_runs_without_creds(self):
        # classify is read-only, no creds needed, no network.
        self.assertEqual(pb.main(["classify", "POST", "/dns/create/example.com"]), 0)


if __name__ == "__main__":
    unittest.main()
