// Verifica di identificativi SINTETICI con i componenti ufficiali scaricati dal codebase del JNLP
// (checkCF_PIVA.jar, controlliXMLREG2013.jar). Uso (Java >= 11, avvio da sorgente singolo):
//   java -cp "<cartella jar>/*" VerificaComponenti.java cf <CF> [<CF> ...]
//   java -cp "<cartella jar>/*" VerificaComponenti.java calcola <cognome> <nome> <M|F> <gg/mm/aaaa> <codice comune>
//   java -cp "<cartella jar>/*" VerificaComponenti.java iban <IBAN> [<IBAN> ...]
// Le classi sono chiamate per riflessione: nessuna dipendenza di compilazione.
import java.lang.reflect.*;

public class VerificaComponenti {
    public static void main(String[] a) throws Exception {
        switch (a[0]) {
            case "cf": {
                Class<?> u1 = Class.forName("finanze.pos.fileutility.U1CheckDigit");
                Class<?> cf = Class.forName("finanze.pos.fileutility.CodiceFiscale");
                Method pf = cf.getMethod("isCodiceFiscalePF", String.class);
                for (int i = 1; i < a.length; i++) {
                    Object o = u1.getConstructor(String.class).newInstance(a[i]);
                    boolean cd = (Boolean) u1.getMethod("controllaCheckDigit").invoke(o);
                    boolean ok = (Boolean) pf.invoke(null, a[i]);
                    System.out.println(a[i] + "\tcheckdigit=" + cd + "\tisCodiceFiscalePF=" + ok);
                }
                break;
            }
            case "calcola": {
                Class<?> cf = Class.forName("finanze.pos.fileutility.CodiceFiscale");
                Object o = cf.getConstructor().newInstance();
                cf.getMethod("setCognome", String.class).invoke(o, a[1]);
                cf.getMethod("setNome", String.class).invoke(o, a[2]);
                cf.getMethod("setSesso", String.class).invoke(o, a[3]);
                cf.getMethod("setDataNascita", String.class).invoke(o, a[4]);
                cf.getMethod("setComune", String.class).invoke(o, a[5]);
                System.out.println(cf.getMethod("getCodiceFiscale").invoke(o));
                break;
            }
            case "iban": {
                Class<?> ck = Class.forName("it.finanze.entrate.sco.modSUC.validator.checkdigit.CheckIBAN");
                Class<?> ib = Class.forName("it.finanze.entrate.sco.generale2013.IBAN");
                for (int i = 1; i < a.length; i++) {
                    Object o = ck.getConstructor().newInstance();
                    Object esito = ck.getMethod("isCorrect", String.class).invoke(o, a[i]);
                    Object cd = ib.getMethod("isCheckDigitValid", String.class).invoke(null, a[i]);
                    String e = esito == null ? "null" : esito.toString().replace("\r", " ").replace("\n", " ");
                    System.out.println(a[i] + "\tisCheckDigitValid=" + cd + "\tCheckIBAN.isCorrect=" + e);
                }
                break;
            }
            default:
                throw new IllegalArgumentException(a[0]);
        }
    }
}
