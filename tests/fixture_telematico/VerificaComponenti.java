// Verifica di identificativi SINTETICI con i componenti ufficiali scaricati dal codebase del JNLP
// (checkCF_PIVA.jar, controlliXMLREG2013.jar). Uso (Java >= 11, avvio da sorgente singolo):
//   java -cp "<cartella jar>/*" VerificaComponenti.java cf <CF> [<CF> ...]
//   java -cp "<cartella jar>/*" VerificaComponenti.java calcola <cognome> <nome> <M|F> <gg/mm/aaaa> <codice comune>
//   java -cp "<cartella jar>/*" VerificaComponenti.java lotto <file>
//   java -cp "<cartella jar>/*" VerificaComponenti.java iban <IBAN> [<IBAN> ...]
// "lotto": file UTF-8, una riga per soggetto, campi separati da TAB:
//   cognome  nome  sesso  gg/mm/aaaa  codice_comune  cf_da_verificare
// stampa per riga: cf, primi 15 caratteri calcolati da finanze.pos.fileutility.CodiceFiscale (il componente
// accoda sempre 'A' come 16o carattere: il carattere di controllo NON e' calcolato da quella classe, vedi
// javap getCodiceFiscale offset 319 "ldc A"), esito di U1CheckDigit.controllaCheckDigit e
// CodiceFiscale.isCodiceFiscalePF sul cf indicato.
// Le classi sono chiamate per riflessione: nessuna dipendenza di compilazione.
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

public class VerificaComponenti {
    static String parziale(String cognome, String nome, String sesso, String data, String comune) throws Exception {
        Class<?> cf = Class.forName("finanze.pos.fileutility.CodiceFiscale");
        Object o = cf.getConstructor().newInstance();
        cf.getMethod("setCognome", String.class).invoke(o, cognome);
        cf.getMethod("setNome", String.class).invoke(o, nome);
        cf.getMethod("setSesso", String.class).invoke(o, sesso);
        cf.getMethod("setDataNascita", String.class).invoke(o, data);
        cf.getMethod("setComune", String.class).invoke(o, comune);
        return (String) cf.getMethod("getCodiceFiscale").invoke(o);
    }

    static String verifica(String codice) throws Exception {
        Class<?> u1 = Class.forName("finanze.pos.fileutility.U1CheckDigit");
        Class<?> cf = Class.forName("finanze.pos.fileutility.CodiceFiscale");
        Object o = u1.getConstructor(String.class).newInstance(codice);
        boolean cd = (Boolean) u1.getMethod("controllaCheckDigit").invoke(o);
        boolean ok = (Boolean) cf.getMethod("isCodiceFiscalePF", String.class).invoke(null, codice);
        return "checkdigit=" + cd + "\tisCodiceFiscalePF=" + ok;
    }

    public static void main(String[] a) throws Exception {
        switch (a[0]) {
            case "cf": {
                for (int i = 1; i < a.length; i++) {
                    System.out.println(a[i] + "\t" + verifica(a[i]));
                }
                break;
            }
            case "calcola": {
                System.out.println(parziale(a[1], a[2], a[3], a[4], a[5]));
                break;
            }
            case "lotto": {
                for (String riga : Files.readAllLines(Paths.get(a[1]), StandardCharsets.UTF_8)) {
                    if (riga.isBlank()) continue;
                    String[] c = riga.split("\t", -1);
                    String p = parziale(c[0], c[1], c[2], c[3], c[4]);
                    System.out.println(c[5] + "\tparziale=" + p.substring(0, 15) + "\t" + verifica(c[5]));
                }
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
