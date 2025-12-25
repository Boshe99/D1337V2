'use client';

import { useChatStore } from '@/store/chat';
import { chatPortalSelectors } from '@/store/chat/slices/portal/selectors';

export const useEnable = () => useChatStore(chatPortalSelectors.showD1337Agent);
