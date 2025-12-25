import { Skeleton } from 'antd';
import { memo, useState } from 'react';
import { Flexbox } from 'react-layout-kit';

// D1337 Agent URL - can be configured via environment variable
const D1337_AGENT_URL = process.env.NEXT_PUBLIC_D1337_AGENT_URL || '/agent';

const D1337AgentBody = memo(() => {
  const [loading, setLoading] = useState(true);

  return (
    <Flexbox
      className={'portal-d1337-agent'}
      flex={1}
      height={'100%'}
      style={{ overflow: 'hidden' }}
    >
      {loading && (
        <Flexbox padding={12}>
          <Skeleton active />
        </Flexbox>
      )}
      <iframe
        allowFullScreen
        height={'100%'}
        hidden={loading}
        onLoad={() => setLoading(false)}
        src={D1337_AGENT_URL}
        style={{
          border: 0,
          flex: 1,
          width: '100%',
        }}
        title="D1337 Agent - Autonomous Coding AI"
      />
    </Flexbox>
  );
});

export default D1337AgentBody;
