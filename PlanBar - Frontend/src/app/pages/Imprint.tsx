import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

interface ImprintData {
  company_name: string;
  address_street: string;
  address_city: string;
  email: string;
  phone: string;
  responsible_person: string;
  eu_odr_link: string;
  dsgvo_contact_email: string;
  dsgvo_data_protection_officer: string;
}

export function Imprint() {
  const [data, setData] = useState<ImprintData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/imprint')
      .then(res => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600" />
      </div>
    );
  }

  if (!data || (!data.company_name && !data.email && !data.responsible_person)) {
    return (
      <div className="py-8">
        <h2 className="text-2xl font-semibold mb-4">Impressum</h2>
        <p className="text-gray-500">Keine Impressumsdaten konfiguriert.</p>
      </div>
    );
  }

  return (
    <div className="py-8 max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-semibold">Impressum</h2>

      {data.company_name && (
        <Card>
          <CardHeader>
            <CardTitle>Angaben zum Verantwortlichen (§5 TMG)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>{data.company_name}</p>
            {data.address_street && <p>{data.address_street}</p>}
            {data.address_city && <p>{data.address_city}</p>}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Kontakt</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {data.email && (
            <p>
              E-Mail:{' '}
              <a href={`mailto:${data.email}`} className="text-blue-600 hover:underline">
                {data.email}
              </a>
            </p>
          )}
          {data.phone && <p>Telefon: {data.phone}</p>}
        </CardContent>
      </Card>

      {data.responsible_person && (
        <Card>
          <CardHeader>
            <CardTitle>Verantwortlich für Inhalte (§55 Abs. 2 RStV)</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{data.responsible_person}</p>
          </CardContent>
        </Card>
      )}

      {data.eu_odr_link && (
        <Card>
          <CardHeader>
            <CardTitle>EU-Streitschlichtung</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="mb-2">
              Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:
            </p>
            <a
              href={data.eu_odr_link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-600 hover:underline"
            >
              {data.eu_odr_link}
              <ExternalLink className="h-3 w-3" />
            </a>
          </CardContent>
        </Card>
      )}

      {data.dsgvo_contact_email && (
        <Card>
          <CardHeader>
            <CardTitle>DSGVO-Kontakt</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>
              E-Mail:{' '}
              <a href={`mailto:${data.dsgvo_contact_email}`} className="text-blue-600 hover:underline">
                {data.dsgvo_contact_email}
              </a>
            </p>
          </CardContent>
        </Card>
      )}

      {data.dsgvo_data_protection_officer && (
        <Card>
          <CardHeader>
            <CardTitle>Datenschutzbeauftragter</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p>{data.dsgvo_data_protection_officer}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
