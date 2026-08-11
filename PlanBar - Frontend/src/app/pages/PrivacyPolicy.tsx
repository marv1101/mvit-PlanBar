import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Separator } from '../components/ui/separator';
import { Shield, User, Cookie, Clock, Mail, FileText, AlertTriangle, Share2, Info } from 'lucide-react';

function Section({ title, icon: Icon, children }: { title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode }) {
  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-lg">
            <Icon className="h-5 w-5 text-blue-700" />
          </div>
          <CardTitle className="text-lg">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="text-sm text-gray-700 leading-relaxed space-y-3">
        {children}
      </CardContent>
    </Card>
  );
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-gray-900">{title}</h3>
      {children}
    </div>
  );
}

export function PrivacyPolicy() {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="text-center mb-10">
        <div className="bg-blue-600 p-4 rounded-full inline-flex mb-4">
          <Shield className="h-8 w-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Datenschutzerklärung</h1>
        <p className="text-gray-500 text-sm">
          Gemäß Art. 13 und 14 der Datenschutz-Grundverordnung (DSGVO)
        </p>
        <p className="text-gray-400 text-xs mt-1">Stand: Juni 2026</p>
      </div>

      <Section title="Verantwortlicher (Art. 4 Nr. 7 DSGVO)" icon={Info}>
        <p>
          Verantwortlicher im Sinne der Datenschutz-Grundverordnung und anderer
          datenschutzrechtlicher Bestimmungen ist:
        </p>
        <div className="bg-gray-50 p-4 rounded-md text-sm">
          <p className="font-semibold">MVIT PlanBar</p>
          <p>Musterstraße 123</p>
          <p>12345 Musterstadt</p>
          <p className="mt-2">
            E-Mail:{' '}
            <a href="mailto:datenschutz@planbar.example.com" className="text-blue-600 hover:underline">
              datenschutz@planbar.example.com
            </a>
          </p>
        </div>
      </Section>

      <Section title="Übersicht der Verarbeitungstätigkeiten" icon={FileText}>
        <p>
          Die MVIT PlanBar ist ein digitales Dienstplan- und Personalmanagement-Tool.
          Im Rahmen der Nutzung der Anwendung verarbeiten wir personenbezogene Daten
          unserer Nutzer und Mitarbeiter zu den nachfolgend beschriebenen Zwecken.
        </p>
      </Section>

      <Section title="Kategorien personenbezogener Daten" icon={User}>
        <SubSection title="Benutzerkonten (User-Accounts)">
          <ul className="list-disc pl-5 space-y-1">
            <li>Benutzername</li>
            <li>E-Mail-Adresse</li>
            <li>Passwort-Hash (nicht das Klartext-Passwort)</li>
            <li>Rolle (Administrator / Mitarbeiter)</li>
            <li>Letzter Login-Zeitpunkt</li>
            <li>Erstellungsdatum des Kontos</li>
          </ul>
        </SubSection>

        <Separator className="my-3" />

        <SubSection title="Mitarbeiterdaten">
          <ul className="list-disc pl-5 space-y-1">
            <li>Vor- und Nachname</li>
            <li>E-Mail-Adresse</li>
            <li>Arbeitszeiten und Schichtzuweisungen</li>
            <li>Vertragsdaten (wöchentliche Arbeitszeit, Vertragsbeginn, -ende)</li>
            <li>Zeitkonto (Guthaben/Stundensaldo)</li>
          </ul>
        </SubSection>

        <Separator className="my-3" />

        <SubSection title="Session-Cookies">
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>access_token:</strong> Sitzungstoken (HTTPOnly, sicher)</li>
            <li><strong>refresh_token:</strong> Erneuerungstoken (HTTPOnly, sicher)</li>
          </ul>
        </SubSection>
      </Section>

      <Section title="Zwecke der Datenverarbeitung" icon={FileText}>
        <SubSection title="Benutzerkonten">
          <ul className="list-disc pl-5 space-y-1">
            <li>Authentifizierung und Autorisierung von Nutzern</li>
            <li>Rollenbasierte Zugriffssteuerung (Admin / Mitarbeiter)</li>
            <li>Sicherstellung der Systemsicherheit und Nachvollziehbarkeit von Änderungen</li>
            <li>Bereitstellung eines persönlichen Zugangs zur Anwendung</li>
          </ul>
        </SubSection>

        <Separator className="my-3" />

        <SubSection title="Mitarbeiterdaten">
          <ul className="list-disc pl-5 space-y-1">
            <li>Erstellung und Verwaltung von Dienstplänen</li>
            <li>Verwaltung von Schichtwünschen und Genehmigungsprozessen</li>
            <li>Erfassung und Nachverfolgung von Arbeitszeiten</li>
            <li>Berechnung von Zeitkonten und Gehaltsabrechnungsgrundlagen</li>
            <li>Sicherstellung einer fairen Schichtverteilung (Fairness-Meter)</li>
          </ul>
        </SubSection>

        <Separator className="my-3" />

        <SubSection title="Session-Cookies">
          <ul className="list-disc pl-5 space-y-1">
            <li>Aufrechterhaltung der Sitzung nach dem Einloggen</li>
            <li>Sicheres Speichern der Authentifizierungsinformationen</li>
            <li>Automatische Verlängerung der Sitzung bei aktiver Nutzung</li>
          </ul>
        </SubSection>
      </Section>

      <Section title="Rechtsgrundlagen der Verarbeitung (Art. 6 Abs. 1 DSGVO)" icon={AlertTriangle}>
        <p className="mb-2">Die Verarbeitung Ihrer personenbezogenen Daten erfolgt auf Grundlage folgender Rechtsvorschriften:</p>

        <div className="space-y-3">
          <div className="bg-blue-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Art. 6 Abs. 1 lit. b DSGVO – Vertragserfüllung</p>
            <p className="text-xs mt-1">
              Die Verarbeitung von Mitarbeiterdaten (Namen, Arbeitszeiten, Vertragsdaten, Zeitkonto)
              ist für die Erfüllung des Arbeitsvertrags sowie für vorvertragliche Maßnahmen erforderlich.
              Ohne diese Daten kann kein Dienstplan erstellt und keine Arbeitszeitverwaltung durchgeführt werden.
            </p>
          </div>

          <div className="bg-blue-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Art. 6 Abs. 1 lit. c DSGVO – Rechtliche Verpflichtung</p>
            <p className="text-xs mt-1">
              Die Verarbeitung von Arbeitszeiten dient der Erfüllung gesetzlicher Aufbewahrungspflichten
              nach § 16 Mutterschutzgesetz, § 22 Jugendarbeitsschutzgesetz sowie der
              Nachweispflicht gemäß § 17 Mindestlohngesetz.
            </p>
          </div>

          <div className="bg-blue-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Art. 6 Abs. 1 lit. f DSGVO – Berechtigtes Interesse</p>
            <p className="text-xs mt-1">
              Die Verarbeitung von Logindaten, Session-Cookies und Zugriffslogs erfolgt auf Basis
              unseres berechtigten Interesses an der Sicherheit und Stabilität der IT-Systeme
              sowie am Schutz vor unbefugtem Zugriff.
            </p>
          </div>

          <div className="bg-blue-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Art. 6 Abs. 1 lit. a DSGVO – Einwilligung</p>
            <p className="text-xs mt-1">
              Soweit wir für bestimmte Verarbeitungen (z. B. erweiterte Profilinformationen)
              Ihre Einwilligung einholen, ist diese Rechtsgrundlage für die Verarbeitung maßgeblich.
              Die Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Speicherdauer" icon={Clock}>
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-semibold text-xs">Benutzerkonten</p>
              <p className="text-xs mt-1">
                Bis zur Löschung des Kontos. Bei Inaktivität von mehr als 12 Monaten behalten wir
                uns die Löschung vor.
              </p>
            </div>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-semibold text-xs">Mitarbeiterdaten</p>
              <p className="text-xs mt-1">
                Für die Dauer des Beschäftigungsverhältnisses zzgl. gesetzlicher
                Aufbewahrungsfristen (i. d. R. 3–10 Jahre nach Beendigung).
              </p>
            </div>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-semibold text-xs">Arbeitszeitdaten</p>
              <p className="text-xs mt-1">
                2 Jahre nach Ende des jeweiligen Kalenderjahres gemäß § 16 Abs. 2 MuSchG
                bzw. § 25 Abs. 2 JArbSchG.
              </p>
            </div>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-semibold text-xs">Session-Cookies</p>
              <p className="text-xs mt-1">
                access_token: 15 Minuten. refresh_token: 7 Tage.
                Nach Ablauf werden diese automatisch gelöscht.
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Im Falle von Rechtsstreitigkeiten können Daten darüber hinaus bis zum Abschluss
            des Verfahrens aufbewahrt werden.
          </p>
        </div>
      </Section>

      <Section title="Ihre Betroffenenrechte (Art. 15–22 DSGVO)" icon={Shield}>
        <p className="mb-3">
          Ihnen stehen als betroffene Person folgende Rechte gegenüber dem Verantwortlichen zu:
        </p>
        <div className="space-y-2">
          <div className="bg-green-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Auskunftsrecht (Art. 15 DSGVO)</p>
            <p className="text-xs mt-1">
              Sie haben das Recht, Auskunft über die von uns verarbeiteten personenbezogenen
              Daten zu verlangen.
            </p>
          </div>
          <div className="bg-green-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Recht auf Berichtigung (Art. 16 DSGVO)</p>
            <p className="text-xs mt-1">
              Sie können die Berichtigung unrichtiger oder Vervollständigung unvollständiger
              Daten verlangen.
            </p>
          </div>
          <div className="bg-green-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Recht auf Löschung (Art. 17 DSGVO)</p>
            <p className="text-xs mt-1">
              Sie können die Löschung Ihrer Daten verlangen, sofern keine gesetzlichen
              Aufbewahrungspflichten entgegenstehen.
            </p>
          </div>
          <div className="bg-green-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Recht auf Einschränkung der Verarbeitung (Art. 18 DSGVO)</p>
            <p className="text-xs mt-1">
              Unter bestimmten Voraussetzungen können Sie die Einschränkung der Verarbeitung verlangen.
            </p>
          </div>
          <div className="bg-green-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Recht auf Datenübertragbarkeit (Art. 20 DSGVO)</p>
            <p className="text-xs mt-1">
              Sie haben das Recht, Ihre Daten in einem maschinenlesbaren Format zu erhalten
              oder an einen anderen Verantwortlichen übermitteln zu lassen.
            </p>
          </div>
          <div className="bg-green-50 p-3 rounded-md">
            <p className="font-semibold text-sm">Widerspruchsrecht (Art. 21 DSGVO)</p>
            <p className="text-xs mt-1">
              Sie können der Verarbeitung Ihrer Daten aus Gründen, die sich aus Ihrer besonderen
              Situation ergeben, jederzeit widersprechen.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Beschwerderecht bei der Aufsichtsbehörde (Art. 77 DSGVO)" icon={AlertTriangle}>
        <p>
          Wenn Sie der Ansicht sind, dass die Verarbeitung Ihrer personenbezogenen Daten
          gegen die DSGVO verstößt, haben Sie unbeschadet anderweitiger Rechtsbehelfe das Recht,
          Beschwerde bei einer Datenschutz-Aufsichtsbehörde einzulegen. Die für uns
          zuständige Aufsichtsbehörde ist:
        </p>
        <div className="bg-gray-50 p-4 rounded-md text-sm mt-2">
          <p className="font-semibold">Der Landesdatenschutzbeauftragte</p>
          <p>Postfach 12 34 56</p>
          <p>12345 Musterstadt</p>
          <p>
            E-Mail:{' '}
            <a href="mailto:poststelle@datenschutz.example.com" className="text-blue-600 hover:underline">
              poststelle@datenschutz.example.com
            </a>
          </p>
        </div>
      </Section>

      <Section title="Datenübermittlung in Drittländer (Art. 44–49 DSGVO)" icon={Share2}>
        <p>
          Eine Übermittlung personenbezogener Daten in Länder außerhalb des Europäischen
          Wirtschaftsraums (EWR) findet nicht statt. Sofern wir Dienste Dritter in Anspruch
          nehmen, erfolgt die Verarbeitung ausschließlich auf Servern innerhalb der
          Europäischen Union.
        </p>
      </Section>

      <Section title="Kontakt bei Datenschutzfragen" icon={Mail}>
        <p>
          Für Fragen zur Verarbeitung Ihrer personenbezogenen Daten, zur Ausübung Ihrer
          Betroffenenrechte oder zu dieser Datenschutzerklärung wenden Sie sich bitte an:
        </p>
        <div className="bg-gray-50 p-4 rounded-md text-sm mt-2">
          <p className="font-semibold">Datenschutzbeauftragter</p>
          <p>MVIT PlanBar</p>
          <p>Musterstraße 123</p>
          <p>12345 Musterstadt</p>
          <p className="mt-2">
            E-Mail:{' '}
            <a href="mailto:datenschutz@planbar.example.com" className="text-blue-600 hover:underline">
              datenschutz@planbar.example.com
            </a>
          </p>
        </div>
      </Section>
    </div>
  );
}
