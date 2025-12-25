'use client';

import { ActionIcon, Icon, Text } from '@lobehub/ui';
import { cx } from 'antd-style';
import { ArrowLeft, Bot, ExternalLink } from 'lucide-react';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Flexbox } from 'react-layout-kit';

import { useChatStore } from '@/store/chat';
import { oneLineEllipsis } from '@/styles';

const Header = memo(() => {
  const { t } = useTranslation('portal');
  const closeD1337Agent = useChatStore((s) => s.closeD1337Agent);

  return (
    <Flexbox align={'center'} flex={1} gap={12} horizontal justify={'space-between'} width={'100%'}>
      <Flexbox align={'center'} gap={8} horizontal>
        <ActionIcon icon={ArrowLeft} onClick={() => closeD1337Agent()} size={'small'} />
        <Icon icon={Bot} size={{ fontSize: 16 }} />
        <Text className={cx(oneLineEllipsis)} type={'secondary'}>
          D1337 Agent - Autonomous Coding AI
        </Text>
      </Flexbox>
      <ActionIcon
        icon={ExternalLink}
        onClick={() => window.open('/agent', '_blank')}
        size={'small'}
        title={t('d1337Agent.openInNewTab', 'Open in new tab')}
      />
    </Flexbox>
  );
});

export default Header;
