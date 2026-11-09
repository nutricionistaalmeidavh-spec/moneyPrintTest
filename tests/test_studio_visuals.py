"""Regression tests for MoneyPrint business-specific slide compositions."""
import unittest
from PIL import Image
from scripts.studio_visuals import business_diagram, paint_layout


class BusinessVisualTests(unittest.TestCase):
    def test_five_systems_get_distinct_diagram_steps(self):
        expected={
            "ERPNext": ("VENDA","ESTOQUE","FINANCEIRO"),
            "Twenty CRM": ("CONTATO","PROPOSTA","VENDA"),
            "Chatwoot": ("MENSAGEM","ATENDENTE","RESOLUÇÃO"),
            "Plane": ("A FAZER","EM ANDAMENTO","CONCLUÍDO"),
            "Paperless-ngx": ("DOCUMENTO","INDEXAÇÃO","BUSCA"),
        }
        for name, labels in expected.items():
            with self.subTest(name=name):
                got,_=business_diagram({"title":name,"eyebrow":name})
                self.assertEqual(got,labels)
                self.assertNotIn("PROCESSO",got)

    def test_all_layouts_draw_elements_for_landscape_and_portrait(self):
        for width,height in [(1920,1080),(1080,1920)]:
            for layout in ("hero","flow","split","browser","quote","minimal"):
                with self.subTest(size=(width,height),layout=layout):
                    image=Image.new("RGB",(width,height),(11,19,33))
                    paint_layout(image,{"title":"ERPNext","eyebrow":"ERPNext","layout":layout},
                                 int(width*.065),int(height*.4),width,height,False)
                    # Layout must change the slide below title; no blank stock fallback.
                    diff=Image.new("RGB",(width,height),(11,19,33))
                    import PIL.ImageChops
                    box=PIL.ImageChops.difference(image,diff).getbbox()
                    self.assertIsNotNone(box)
                    self.assertGreater(box[3],height*.45)


if __name__=="__main__":
    unittest.main()
