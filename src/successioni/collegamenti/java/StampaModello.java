// Stampa del modello ministeriale SUC13 con il codice Java del componente di controllo dell'Agenzia (sola lettura, locale).
// Catena (verificata il 2026-11-05): XML (busta tm + suc:Fornitura) -> SUCFornituraDocumentService -> SUCConverter.getDichiarazioneMap
//   -> PrintModel(mappa campi, extra{codiceFiscale}, ids quadri) -> overlay dei valori sui PDF modello ufficiali (template Jasper).
// Uso:  java -Djava.awt.headless=true -cp "<cartella di questo file>;<cartella componente>/*" StampaModello in.xml out.pdf
// Compilare con scripts/compila_stampa.py (javac --release 8): il risultato (StampaModello.class) e' versionato.
import java.io.*;
import java.util.*;
import javax.xml.parsers.*;
import javax.xml.transform.*;
import javax.xml.transform.dom.*;
import javax.xml.transform.stream.*;
import org.w3c.dom.*;
import it.finanze.entrate.sfe.suc.service.SUCFornituraDocumentService;
import it.finanze.entrate.sfe.suc.converter.SUCConverter;
import itSpecificheTecnicheScoSucV1.gov.agenziaentrate.*;
import it.sogei.entrate.sfe.PrintModel;

public class StampaModello {
  public static void main(String[] a) throws Exception {
    DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
    f.setNamespaceAware(true);
    f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);   // niente entita' esterne
    Document d = f.newDocumentBuilder().parse(new File(a[0]));
    NodeList nl = d.getElementsByTagNameNS("*", "Fornitura");
    Element forn = null;
    for (int i = 0; i < nl.getLength(); i++) if (((Element) nl.item(i)).getNamespaceURI().contains("suc")) forn = (Element) nl.item(i);
    if (forn == null) throw new RuntimeException("Fornitura SUC non trovata");
    ByteArrayOutputStream bo = new ByteArrayOutputStream();
    TransformerFactory.newInstance().newTransformer().transform(new DOMSource(forn), new StreamResult(bo));
    FornituraDocument fd = new SUCFornituraDocumentService(new ByteArrayInputStream(bo.toByteArray())).getFornitura();
    DichiarazioneSUCType dich = fd.getFornitura2().getDichiarazione();
    Map<String, String> m = new SUCConverter().getDichiarazioneMap(dich, "PrimoModulo");
    Map<String, String> filtrata = new HashMap<String, String>();
    for (Map.Entry<String, String> e : m.entrySet()) {
      String k = e.getKey();
      if (k.length() == 16) filtrata.put(k, e.getValue());
      else if (k.matches("#B[0-9]{3}") && Integer.parseInt(k.substring(2)) >= 11) filtrata.put("AN000" + k.substring(2) + "00000001", e.getValue());
    }
    Map<String, Object> extra = new HashMap<String, Object>();
    extra.put("codiceFiscale", m.get("#B002"));        // intestazione di ogni pagina: codice fiscale del defunto
    List<String> quadri = new ArrayList<String>();
    for (int i = 1; i <= 19; i++) quadri.add(String.format("%02d", i));
    PrintModel.init();
    ByteArrayOutputStream pdf = new PrintModel(filtrata, extra, quadri).printPdfStream();
    try (FileOutputStream fo = new FileOutputStream(a[1])) { fo.write(pdf.toByteArray()); }
    System.out.println("CAMPI=" + filtrata.size() + " PDF=" + pdf.size());
    System.exit(0);
  }
}
