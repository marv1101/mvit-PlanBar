import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Separator } from '../components/ui/separator';
import { Building2, Mail, Phone, FileText, Shield, Info, AlertTriangle, User, Link as LinkIcon } from 'lucide-react';

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

export function Imprint() {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="text-center mb-10">
        <div className="bg-blue-600 p-4 rounded-full inline-flex mb-4">
          <Building2 className="h-8 w-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Impressum</h1>
        <p className="text-gray-500 text-sm">
          Angaben gemäß § 5 TMG und § 18 TTDSG
        </p>
        <p className="text-gray-400 text-xs mt-1">Stand: Juli 2026</p>
      </div>

      <Section title="Verantwortlicher" icon={Building2}>
        <div className="bg-gray-50 p-4 rounded-md text-sm">
          <p className="font-semibold">MVIT PlanBar GmbH</p>
          <p>Musterstraße 123</p>
          <p>12345 Musterstadt</p>
          <p>Deutschland</p>
        </div>
        <p className="mt-3">
          <span className="font-semibold">Vertreten durch:</span>
          <br />
          Max Mustermann (Geschäftsführer)
        </p>
      </Section>

      <Section title="Kontakt" icon={Phone}>
        <div className="space-y-2">
          <p>
            <span className="font-semibold">E-Mail:</span>{' '}
            <a href="mailto:info@planbar.example.com" className="text-blue-600 hover:underline">
              info@planbar.example.com
            </a>
          </p>
          <p>
            <span className="font-semibold">Telefon:</span> +49 (0) 123 456789
          </p>
          <p>
            <span className="font-semibold">Fax:</span> +49 (0) 123 456780
          </p>
        </div>
      </Section>

      <Section title="Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV" icon={User}>
        <div className="bg-gray-50 p-4 rounded-md text-sm">
          <p>Max Mustermann</p>
          <p>Musterstraße 123</p>
          <p>12345 Musterstadt</p>
        </div>
      </Section>

      <Section title="Registereintrag" icon={FileText}>
        <p>
          <span className="font-semibold">Eintragung im Handelsregister:</span>
        </p>
        <p>Registergericht: Amtsgericht Musterstadt</p>
        <p>Registernummer: HRB 12345</p>
      </Section>

      <Section title="Umsatzsteuer-ID" icon={Info}>
        <p>
          Umsatzsteuer-Identifikationsnummer gemäß §27 a Umsatzsteuergesetz:
        </p>
        <p className="font-mono bg-gray-50 p-2 rounded">DE123456789</p>
      </Section>

      <Section title="Streitschlichtung" icon={AlertTriangle}>
        <p>
          Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{' '}
          <a
            href="https://ec.europa.eu/consumers/odr"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline inline-flex items-center gap-1"
          >
            https://ec.europa.eu/consumers/odr
            <LinkIcon className="h-3 w-3" />
          </a>
        </p>
        <p>
          Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen.
        </p>
      </Section>

      <Separator className="my-6" />

      <Section title="Haftungsausschluss" icon={Shield}>
        <SubSection title="Haftung für Inhalte">
          <p>
            Die Inhalte unserer Seiten wurden mit größter Sorgfalt erstellt. Für die Richtigkeit,
            Vollständigkeit und Aktualität der Inhalte können wir jedoch keine Gewähr übernehmen.
            Als Diensteanbieter sind wir gemäß § 7 Abs.1 TMG für eigene Inhalte auf diesen Seiten
            nach den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 TMG sind wir als
            Diensteanbieter jedoch nicht verpflichtet, übermittelte oder gespeicherte fremde
            Informationen zu überwachen oder nach Umständen zu forschen, die auf eine rechtswidrige
            Tätigkeit hinweisen.
          </p>
        </SubSection>

        <Separator className="my-3" />

        <SubSection title="Haftung für Links">
          <p>
            Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen
            Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine Gewähr
            übernehmen. Für die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder
            Betreiber der Seiten verantwortlich.
          </p>
        </SubSection>

        <Separator className="my-3" />

        <SubSection title="Urheberrecht">
          <p>
            Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen
            dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art
            der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen
            Zustimmung des jeweiligen Autors bzw. Erstellers.
          </p>
        </SubSection>
      </Section>

      <Separator className="my-6" />

      <Section title="DSGVO-Kontakt" icon={Mail}>
        <p>
          Für Anfragen gemäß der Datenschutz-Grundverordnung (DSGVO) kontaktieren Sie uns bitte unter:
        </p>
        <div className="bg-gray-50 p-4 rounded-md text-sm space-y-2">
          <p>
            <span className="font-semibold">E-Mail:</span>{' '}
            <a href="mailto:datenschutz@planbar.example.com" className="text-blue-600 hover:underline">
              datenschutz@planbar.example.com
            </a>
          </p>
          <p>
            <span className="font-semibold">Betreff:</span> DSGVO-Anfrage
          </p>
        </div>
        <p className="mt-3 font-semibold">Ihre Rechte nach DSGVO:</p>
        <ul className="list-disc pl-5 space-y-1 text-sm">
          <li>Art. 15 DSGVO: Auskunftsrecht</li>
          <li>Art. 16 DSGVO: Recht auf Berichtigung</li>
          <li>Art. 17 DSGVO: Recht auf Löschung</li>
          <li>Art. 18 DSGVO: Recht auf Einschränkung der Verarbeitung</li>
          <li>Art. 20 DSGVO: Recht auf Datenübertragbarkeit</li>
          <li>Art. 21 DSGVO: Widerspruchsrecht</li>
        </ul>
      </Section>

      <Separator className="my-6" />

      <Section title="Datenschutzbeauftragter" icon={Shield}>
        <p>
          Bei Fragen zum Datenschutz erreichen Sie unseren Datenschutzbeauftragten unter:
        </p>
        <div className="bg-gray-50 p-4 rounded-md text-sm">
          <p>
            <span className="font-semibold">E-Mail:</span>{' '}
            <a href="mailto:datenschutz@planbar.example.com" className="text-blue-600 hover:underline">
              datenschutz@planbar.example.com
            </a>
          </p>
        </div>
        <p className="mt-3">
          Weitere Informationen finden Sie in unserer{' '}
          <a href="/privacy" className="text-blue-600 hover:underline">
            Datenschutzerklärung
          </a>
          .
        </p>
      </Section>

      <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
        <p className="font-semibold mb-1">Hinweis:</p>
        <p>
          Dieses Impressum dient als Vorlage und ersetzt keine Rechtsberatung. Für verbindliche
          Auskünfte sollte ein Jurist konsultiert werden.
        </p>
      </div>
    </div>
  );
}
