import { Bot } from 'lucide-react';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';

import { useChatStore } from '@/store/chat';

import Action from '../components/Action';

const D1337Agent = memo(() => {
  const { t } = useTranslation('chat');
  const openD1337Agent = useChatStore((s) => s.openD1337Agent);

  return (
    <Action
      icon={Bot}
      onClick={openD1337Agent}
      title={t('d1337Agent.title', 'D1337 Agent')}
      tooltipProps={{
        placement: 'bottom',
      }}
    />
  );
});

export default D1337Agent;
