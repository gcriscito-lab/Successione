import unittest
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from successioni.valori import parse_importo, parse_quota, ValoreNonValido, e_stato
from successioni.schema import valida_campo, Errore

class TestValoriSchemaExtra(unittest.TestCase):
    def test_parse_importo(self):
        # Test importo valido
        self.assertEqual(parse_importo("100.50"), Decimal("100.50"))
        # Test importo con virgola
        with self.assertRaises(ValoreNonValido):
            parse_importo("100,50")
        # Test importo float
        with self.assertRaises(ValoreNonValido):
            parse_importo(100.50)
        # Test importo stringa vuota
        with self.assertRaises(ValoreNonValido):
            parse_importo("")

    def test_parse_quota(self):
        # Test quota valida
        self.assertEqual(parse_quota({"num": 1, "den": 2}), Fraction(1, 2))
        self.assertEqual(parse_quota("1/2"), Fraction(1, 2))
        # Test denominatore zero
        with self.assertRaises(ValoreNonValido):
            parse_quota({"num": 1, "den": 0})
        # Test denominatore negativo
        with self.assertRaises(ValoreNonValido):
            parse_quota({"num": 1, "den": -1})
        # Test numeratore negativo
        with self.assertRaises(ValoreNonValido):
            parse_quota({"num": -1, "den": 2})
        # Test quota maggiore di 1
        with self.assertRaises(ValoreNonValido):
            parse_quota({"num": 3, "den": 2})

    def test_e_stato(self):
        # Test stato valido
        self.assertTrue(e_stato({"stato": "assente"}))
        self.assertTrue(e_stato({"stato": "zero"}))
        self.assertTrue(e_stato({"stato": "non_applicabile"}))
        self.assertTrue(e_stato({"stato": "da_confermare"}))
        # Test stato non valido
        self.assertFalse(e_stato({"stato": "valido"}))
        self.assertFalse(e_stato({"stato": ""}))
        self.assertFalse(e_stato({"stato": 1}))

    def test_valida_campo(self):
        # Test campo valido
        self.assertEqual(valida_campo("str", "test", "test", {}), [])
        self.assertEqual(valida_campo("cf", "ABCDEFGHIJKLMNOP", "test", {}), [])
        self.assertEqual(valida_campo("data", "2023-01-01", "test", {}), [])
        self.assertEqual(valida_campo("quota", {"num": 1, "den": 2}, "test", {}), [])
        self.assertEqual(valida_campo("importo", "100.50", "test", {}), [])
        self.assertEqual(valida_campo("enum:a|b", "a", "test", {}), [])
        # Test campo non valido
        self.assertEqual(valida_campo("str", 123, "test", {}), [Errore("VALORE_NON_VALIDO", "test", "atteso testo")])
        self.assertEqual(valida_campo("cf", "ABCDEFGHIJKLMN", "test", {}), [Errore("VALORE_NON_VALIDO", "test", "codice fiscale di 16 caratteri alfanumerici (lettere e cifre, senza spazi)")])
        self.assertEqual(valida_campo("data", "2023-02-29", "test", {}), [Errore("VALORE_NON_VALIDO", "test", "data inesistente nel calendario")])
        self.assertEqual(valida_campo("quota", {"num": 1, "den": 0}, "test", {}), [Errore("VALORE_NON_VALIDO", "test", "denominatore > 0 e numeratore >= 0")])
        self.assertEqual(valida_campo("importo", "100,50", "test", {}), [Errore("VALORE_NON_VALIDO", "test", "separatore decimale ',' non ammesso: usare il punto (esempio 1234.50)")])
        self.assertEqual(valida_campo("enum:a|b", "c", "test", {}), [Errore("VALORE_NON_VALIDO", "test", "valore ammesso: a, b")])

if __name__ == '__main__':
    unittest.main()