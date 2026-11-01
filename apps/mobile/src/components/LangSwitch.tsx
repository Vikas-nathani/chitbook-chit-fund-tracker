import { Chip, Row } from '@/components/ui';
import { useI18n } from '@/i18n';

/** English / తెలుగు switch. The choice is remembered on this device. */
export function LangSwitch() {
  const { lang, setLang } = useI18n();
  return (
    <Row>
      <Chip label="English" active={lang === 'en'} onPress={() => setLang('en')} />
      <Chip label="తెలుగు" active={lang === 'te'} onPress={() => setLang('te')} />
    </Row>
  );
}
