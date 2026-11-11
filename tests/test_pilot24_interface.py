"""Regression contracts for natural app demos with provenance kept off screen."""
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
from scripts.pilot24_editor import Stage, frame_at
from scripts.pilot24_live_ui import allowed_capture_target, is_readable_app, has_visible_main_content, crop_demo_chrome

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

    def test_empty_app_main_panel_must_be_rejected_even_with_sidebar(self):
        image=Image.new("RGB",(1440,900),"white")
        d=ImageDraw.Draw(image)
        d.rectangle((0,0,300,900),fill=(244,244,244))
        d.text((70,260),"Selling Stock CRM",fill=(30,30,30))
        self.assertFalse(has_visible_main_content(image))
        d.rectangle((360,230,1250,610),fill=(239,244,247))
        for y in range(258,570,42):
            d.text((407,y),"Sales orders customer product 2026",fill=(32,45,62))
        self.assertTrue(has_visible_main_content(image))

    def test_demo_trial_banner_is_cropped_without_changing_app_content(self):
        image=Image.new("RGB",(1440,900),(247,248,249))
        d=ImageDraw.Draw(image)
        d.rectangle((0,40,1439,83),fill=(208,232,243))
        d.rectangle((300,180,1200,790),fill=(233,238,240))
        cropped=crop_demo_chrome(image)
        self.assertLess(cropped.height,900)
        self.assertEqual(cropped.getpixel((500,0)),(247,248,249))
        self.assertEqual(cropped.getpixel((500,200)),(233,238,240))

    def test_actual_selling_stock_and_readme_proofs_replace_loading_home(self):
        repo=Image.new("RGB",(1440,900),(21,24,30))
        app=Image.new("RGB",(838,534),(230,230,230))
        home=Image.new("RGB",(1440,900),(250,250,250))
        selling=Image.new("RGB",(1440,900),(111,40,40))
        stock=Image.new("RGB",(1440,900),(20,115,35))
        picks=[]
        original=Stage.screenshot
        def spy(self,source,rect,*args,**kwargs):
            picks.append(source)
            return original(self,source,rect,*args,**kwargs)
        with patch.object(Stage,"screenshot",spy):
            for sec in (16.2,19.0,22.0):
                frame_at(sec,repo,app,640,360,
                    ui_screens={"home":home,"selling":selling,"stock":stock})
        self.assertIs(picks[0],selling)
        self.assertIs(picks[1],stock)
        self.assertIs(picks[2],app)

    def test_live_views_are_optional_and_real_screens_take_main_stage(self):
        repo=Image.new("RGB",(1440,900),(29,40,51))
        app=Image.new("RGB",(838,534),(242,241,240))
        selling=Image.new("RGB",(1440,900),(120,40,20))
        stock=Image.new("RGB",(1440,900),(10,130,30))
        a=frame_at(19,repo,app,640,360,ui_screens={"selling":selling,"stock":stock})
        b=frame_at(22,repo,app,640,360,ui_screens={"selling":selling,"stock":stock})
        self.assertNotEqual(a.tobytes(),b.tobytes())

if __name__=="__main__":unittest.main()
