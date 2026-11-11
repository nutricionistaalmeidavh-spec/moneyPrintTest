"""Regression contracts for natural app demos with provenance kept off screen."""
import unittest
from unittest.mock import patch
from PIL import Image
from scripts.pilot24_editor import Stage, frame_at
from scripts.pilot24_live_ui import allowed_capture_target, is_readable_app

class InterfaceFirstPilotTests(unittest.TestCase):
    def test_demo_navigation_never_visits_unknown_hosts(self):
        self.assertTrue(allowed_capture_target("https://erpnext-demo.frappe.cloud/app/selling"))
        self.assertTrue(allowed_capture_target("https://erpnext-demo.frappe.cloud/app/stock"))
        self.assertFalse(allowed_capture_target("https://example.org/app/selling"))
        self.assertFalse(allowed_capture_target("http://erpnext-demo.frappe.cloud/app/selling"))
        self.assertFalse(allowed_capture_target("https://erpnext-demo.frappe.cloud.evil.test/app/stock"))

    def test_login_screen_cannot_be_mislabeled_as_app(self):
        self.assertFalse(is_readable_app("https://erpnext-demo.frappe.cloud/login", "Login to Frappe"))
        self.assertFalse(is_readable_app("https://erpnext-demo.frappe.cloud/app/home", ""))
        self.assertTrue(is_readable_app("https://erpnext-demo.frappe.cloud/app/selling", "Selling Customers Quotations Sales Orders"))

    def test_pilot_has_no_on_screen_provenance_qa_or_mockup_disclaimers(self):
        repo=Image.new("RGB",(1440,900),(29,40,51))
        app=Image.new("RGB",(838,534),(242,241,240))
        called=[]
        original=Stage.tx
        def spy(self,x,y,msg,*args,**kwargs):
            called.append(str(msg))
            return original(self,x,y,msg,*args,**kwargs)
        with patch.object(Stage,"tx",spy):
            for sec in (13,16,19,22):
                frame_at(sec,repo,app,640,360)
        visible=" ".join(called).casefold()
        for forbidden in ("captura", "readme", "mockup", "fictíci", "imagem estática",
                          "fonte:", "prova de interface", "tela real", "24s",
                          "repositório verificável", "fluxo didático"):
            self.assertNotIn(forbidden,visible)

    def test_live_views_are_optional_and_real_screens_take_main_stage(self):
        repo=Image.new("RGB",(1440,900),(29,40,51))
        app=Image.new("RGB",(838,534),(242,241,240))
        selling=Image.new("RGB",(1440,900),(120,40,20))
        stock=Image.new("RGB",(1440,900),(10,130,30))
        a=frame_at(19,repo,app,640,360,ui_screens={"selling":selling,"stock":stock})
        b=frame_at(22,repo,app,640,360,ui_screens={"selling":selling,"stock":stock})
        self.assertNotEqual(a.tobytes(),b.tobytes())

if __name__=="__main__":unittest.main()
