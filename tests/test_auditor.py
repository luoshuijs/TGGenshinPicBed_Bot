import unittest
from src.model.artwork import AuditInfo, AuditStatus, AuditType
from src.production.auditor import Auditor, ArtworkStatusUpdate


class TestAuditor(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def test_audit_status_always_updates(self):
        # 1. Setup
        status = AuditStatus.PASS
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = Auditor.audit(sut, status)
        # 3. Compare
        self.assertEqual(status_update.new_status, status.value)

    def test_audit_type_does_not_update_when_None(self):
        # 1. Setup
        audit_type = None
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = Auditor.audit(sut, AuditStatus.INIT, new_type=audit_type)
        # 3. Compare
        self.assertEqual(status_update.new_type, AuditType.SFW.value)

    def test_audit_type_updates_when_not_None(self):
        # 1. Setup
        audit_type = AuditType.NSFW
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        # 2. Execute
        status_update = Auditor.audit(sut, AuditStatus.INIT, new_type=audit_type)
        # 3. Compare
        self.assertEqual(status_update.new_type, audit_type.value)

    def test_audit_reason_updates_when_not_None(self):
        # 1. Setup
        reason = "类型错误"
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT, audit_reason=None)
        # 2. Execute
        status_update = Auditor.audit(sut, AuditStatus.INIT, new_reason=reason)
        # 3. Compare
        self.assertEqual(status_update.new_reason, reason)

    def test_audit_reason_does_not_update_when_None(self):
        # 1. Setup
        reason = None
        sut = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT, audit_reason="质量差")
        # 2. Execute
        status_update = Auditor.audit(sut, AuditStatus.INIT, new_reason=reason)
        # 3. Compare
        self.assertEqual(status_update.new_reason, "质量差")

    def test_can_update_is_true_when_new_attributes_are_different_than_current_ones(self):
        # 1. Setup
        audit_info = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        sut = Auditor.audit(audit_info, AuditStatus.PASS)
        # 2. Execute
        can_update = sut.can_update()
        # 3. Compare
        self.assertTrue(can_update)

    def test_can_update_is_false_when_new_attributes_are_same_as_current_ones(self):
        # 1. Setup
        audit_info = AuditInfo(0, 0, 0, audit_type=AuditType.SFW, audit_status=AuditStatus.INIT)
        sut = Auditor.audit(audit_info, AuditStatus.INIT)
        # 2. Execute
        can_update = sut.can_update()
        # 3. Compare
        self.assertFalse(can_update)

    def test_exception_when_audit_info_not_available(self):
        with self.assertRaises(AttributeError):
            sut = Auditor.audit(None, AuditStatus.PASS)


if __name__ == "__main__":
    unittest.main()
