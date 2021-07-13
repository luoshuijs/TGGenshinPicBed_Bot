import unittest
from src.model.artwork import AuditInfo, AuditStatus, AuditType
from src.production.auditor import approve, reject, push, ArtworkStatusUpdate


class TestAuditor(unittest.TestCase):

    def test_audit_approves_init_status(self):
        # 1. Setup
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = approve(sut)
        # 3. Compare
        self.assertEqual(status_update.new_status, AuditStatus.PASS.value)

    def test_audit_status_does_not_change_when_approving_non_init_status(self):
        # 1. Setup
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.PASS)
        # 2. Execute
        status_update = approve(sut)
        # 3. Compare
        self.assertEqual(status_update.new_status, AuditStatus.PASS.value)

    def test_audit_non_type_changes_to_sfw_when_approving(self):
        # 1. Setup
        sut = AuditInfo(0, 0, 0, audit_type=None, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = approve(sut)
        # 3. Compare
        self.assertEqual(status_update.new_type, AuditType.SFW.value)
        self.assertEqual(status_update.new_status, AuditStatus.PASS.value)

    def test_audit_reason_updates_on_reject_when_not_None(self):
        # 1. Setup
        reason = "类型错误"
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT, audit_reason=None)
        # 2. Execute
        status_update = reject(sut, reason=reason)
        # 3. Compare
        self.assertEqual(status_update.new_reason, reason)

    def test_audit_reason_does_not_update_on_reject_when_None(self):
        # 1. Setup
        reason = None
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT, audit_reason="质量差")
        # 2. Execute
        status_update = reject(sut, reason=reason)
        # 3. Compare
        self.assertEqual(status_update.new_reason, "质量差")

    def test_type_and_status_is_updated_when_sfw_art_is_rejected_for_nsfw(self):
        # 1. Setup
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = reject(sut, reason="NSFW")
        # 3. Compare
        self.assertEqual(status_update.new_status, AuditStatus.INIT.value)
        self.assertEqual(status_update.new_type, AuditType.NSFW.value)

    def test_audit_type_is_r18_when_non_r18_art_is_rejected_as_r18(self):
        # 1. Setup
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.NSFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = reject(sut, reason="R18")
        # 3. Compare
        self.assertEqual(status_update.new_status, AuditStatus.INIT.value)
        self.assertEqual(status_update.new_type, AuditType.R18.value)

    def test_push_status_updates(self):
        # 1. Setup
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.NSFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = push(sut)
        # 3. Compare
        self.assertEqual(status_update.new_status, AuditStatus.PUSH.value)
        self.assertEqual(status_update.new_type, AuditType.NSFW.value)

    def test_can_update_is_true_when_new_attributes_are_different_than_current_ones(self):
        # 1. Setup
        audit_info = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        sut = approve(audit_info)
        # 2. Execute
        can_update = sut.can_update()
        # 3. Compare
        self.assertTrue(can_update)

    def test_can_update_is_false_when_new_attributes_are_same_as_current_ones(self):
        # 1. Setup
        audit_info = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.PASS)
        sut = approve(audit_info)
        # 2. Execute
        can_update = sut.can_update()
        # 3. Compare
        self.assertFalse(can_update, f"""
                {audit_info.audit_type} vs {sut.new_type}
                {audit_info.audit_status} vs {sut.new_status}
                {audit_info.audit_reason} vs {sut.new_reason}""")

    def test_exception_when_audit_info_not_available(self):
        with self.assertRaises(Exception):
            sut = approve(None)
        with self.assertRaises(Exception):
            sut = approve(None)
