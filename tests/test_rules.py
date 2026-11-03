import unittest

from scamscan.rules import FREE_EMAIL_DOMAINS, analyze_rules

from . import samples


def codes(text):
    return analyze_rules(text).codes


class FeeRequestTests(unittest.TestCase):
    def test_fee_request_is_a_hard_flag(self):
        result = analyze_rules("Pay a registration fee of AED 450 to confirm your slot.")
        self.assertIn("fee_request", result.codes)
        self.assertTrue(result.has_hard)

    def test_negated_fee_is_not_flagged(self):
        self.assertNotIn("fee_request", codes("There is no registration fee at any stage."))
        self.assertNotIn("fee_request", codes("You do not need to pay anything to apply."))

    def test_applicant_must_pay_is_flagged(self):
        self.assertIn("fee_request", codes("Candidates must pay for the visa upfront."))


class FinancialAndIdTests(unittest.TestCase):
    def test_bank_details_request_is_hard(self):
        result = analyze_rules("Please share your bank details to start payroll.")
        self.assertIn("financial_details", result.codes)
        self.assertTrue(result.has_hard)

    def test_otp_mention_is_flagged_but_warning_against_it_is_not(self):
        self.assertIn("financial_details", codes("Tell us the OTP you receive."))
        self.assertNotIn("financial_details", codes("Never share your OTP with anyone."))

    def test_passport_request_is_a_soft_flag(self):
        result = analyze_rules("Send your CV and passport copy to the hiring team.")
        self.assertIn("id_documents", result.codes)
        self.assertNotIn("financial_details", result.codes)
        self.assertFalse(result.has_hard)


class EmailTests(unittest.TestCase):
    def test_free_email_is_flagged(self):
        self.assertIn("free_email", codes("Send your CV to someone@gmail.com"))

    def test_generic_handle_weighs_more_than_a_personal_looking_one(self):
        generic = analyze_rules("Apply at dubai.jobs.team@gmail.com")
        personal = analyze_rules("Apply at maria.santos@gmail.com")
        weight = {f.code: f.weight for f in generic.flags}["free_email"]
        personal_weight = {f.code: f.weight for f in personal.flags}["free_email"]
        self.assertGreater(weight, personal_weight)

    def test_company_domain_email_is_a_positive_and_not_flagged(self):
        result = analyze_rules("Apply at careers@acme-logistics.example")
        self.assertNotIn("free_email", result.codes)
        self.assertIn("corporate_email", {p.code for p in result.positives})

    def test_free_domain_list_contains_common_providers(self):
        for domain in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com"):
            self.assertIn(domain, FREE_EMAIL_DOMAINS)


class OtherRuleTests(unittest.TestCase):
    def test_vague_ad_is_flagged(self):
        self.assertIn("vague_ad", codes("We are hiring staff in Dubai. Send your CV."))

    def test_detailed_ad_is_not_vague(self):
        self.assertNotIn("vague_ad", codes(samples.LEGIT_DETAILED))

    def test_too_good_to_be_true_is_flagged(self):
        self.assertIn("too_good", codes("Earn AED 500 per day from home, guaranteed income."))
        self.assertIn("too_good", codes("No interview needed, start tomorrow."))

    def test_urgency_is_flagged(self):
        self.assertIn("urgency", codes("Apply now! Limited seats available."))

    def test_messaging_only_is_flagged_without_other_contact(self):
        self.assertIn("messaging_only", codes("Message us on WhatsApp to apply."))

    def test_messaging_not_flagged_when_company_email_present(self):
        text = "Apply at careers@acme-logistics.example or message us on WhatsApp."
        self.assertNotIn("messaging_only", codes(text))

    def test_missing_company_and_contact_are_flagged(self):
        result = analyze_rules(samples.NO_COMPANY_NO_CONTACT)
        self.assertIn("no_company", result.codes)
        self.assertIn("no_verifiable_contact", result.codes)


class SampleAdTests(unittest.TestCase):
    def test_empty_text_has_no_flags_and_zero_score(self):
        for text in ("", "   ", None):
            result = analyze_rules(text)
            self.assertEqual(result.flags, ())
            self.assertEqual(result.rule_prob, 0.0)

    def test_scam_sample_hits_the_expected_rules_and_maxes_out(self):
        result = analyze_rules(samples.SCAM_FEE)
        for code in ("fee_request", "financial_details", "id_documents", "too_good", "urgency"):
            self.assertIn(code, result.codes)
        self.assertTrue(result.has_hard)
        self.assertEqual(result.rule_prob, 1.0)

    def test_vague_free_email_sample_scores_high_but_not_hard(self):
        result = analyze_rules(samples.VAGUE_FREE_EMAIL)
        self.assertEqual({"free_email", "vague_ad", "no_company"}, set(result.codes))
        self.assertFalse(result.has_hard)
        self.assertGreaterEqual(result.rule_prob, 0.55)

    def test_legit_sample_has_no_flags_and_several_positives(self):
        result = analyze_rules(samples.LEGIT_DETAILED)
        self.assertEqual(result.flags, ())
        self.assertEqual(result.rule_prob, 0.0)
        self.assertGreaterEqual(len(result.positives), 4)

    def test_no_company_sample_is_medium(self):
        result = analyze_rules(samples.NO_COMPANY_NO_CONTACT)
        self.assertGreaterEqual(result.rule_prob, 0.25)
        self.assertLess(result.rule_prob, 0.55)

    def test_positives_lower_the_score(self):
        bare = analyze_rules("Hiring staff. Send CV to someone@gmail.com")
        with_site = analyze_rules("Hiring staff. Send CV to someone@gmail.com https://acme.example")
        self.assertLess(with_site.raw_score, bare.raw_score)

    def test_probability_is_always_between_zero_and_one(self):
        for text in (samples.SCAM_FEE, samples.VAGUE_FREE_EMAIL, samples.LEGIT_DETAILED,
                     samples.NO_COMPANY_NO_CONTACT, "x"):
            self.assertTrue(0.0 <= analyze_rules(text).rule_prob <= 1.0)


if __name__ == "__main__":
    unittest.main()
