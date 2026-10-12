'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Send, Sparkles, Phone, UserRound } from 'lucide-react';
import { api, errorMessage, useBusiness, useIntegrations } from '../../src/lib/api';
import { formatTime, initials, relativeTime } from '../../src/lib/format';
import { useNow } from '../../src/lib/useNow';
import StatusBadge from '../../src/components/StatusBadge';
import type { Conversation, Message } from '../../src/lib/types';

export default function ConversationsPage() {
  const queryClient = useQueryClient();
  const now = useNow(30_000);
  const { data: business } = useBusiness();
  const { data: integrations } = useIntegrations();
  const { data: conversations = [], isLoading, isError } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => (await api.get<Conversation[]>('/conversations/')).data,
    refetchInterval: 10_000,
  });

  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const activeConv = conversations.find((c) => c.client_id === activeConvId) ?? conversations[0];

  const { mutate: markRead } = useMutation({
    mutationFn: (clientId: number) => api.post(`/conversations/${clientId}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  });
  useEffect(() => {
    if (activeConv?.unread) markRead(activeConv.client_id);
  }, [activeConv?.client_id, activeConv?.unread, markRead]);

  const agentActive = Boolean(business?.outreach_enabled && integrations?.twilio.configured);

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <header className="p-6 bg-white border-b border-gray-100 flex-shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
          <p className="text-sm text-gray-500">Monitor WhatsApp negotiations and intervene if necessary.</p>
        </div>
        {integrations && (
          agentActive ? (
            <div className="flex items-center text-sm text-green-600 bg-green-50 px-3 py-1.5 rounded-lg font-medium border border-green-100">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
              AI Agent Active
            </div>
          ) : (
            <div className="flex items-center text-sm text-gray-600 bg-gray-100 px-3 py-1.5 rounded-lg font-medium border border-gray-200">
              <span className="w-2 h-2 bg-gray-400 rounded-full mr-2"></span>
              {integrations.twilio.configured ? 'Outreach Disabled' : 'WhatsApp Not Configured'}
            </div>
          )
        )}
      </header>

      {/* Main Panel */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Side: Conversational List */}
        <div className="w-96 bg-white border-r border-gray-100 flex flex-col flex-shrink-0 h-full overflow-y-auto">
          {!isLoading && conversations.length === 0 && (
            <p className="p-6 text-sm text-gray-500">
              {isError ? 'Could not load conversations.' : 'No conversations yet. They appear here once the AI contacts a client or a client messages you.'}
            </p>
          )}
          <div className="divide-y divide-gray-100">
            {conversations.map((conv) => (
              <button
                key={conv.client_id}
                onClick={() => setActiveConvId(conv.client_id)}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors flex flex-col ${
                  activeConv?.client_id === conv.client_id ? 'bg-blue-50/50 hover:bg-blue-50/50 border-l-4 border-blue-600' : ''
                }`}
              >
                <div className="flex justify-between items-start w-full mb-1">
                  <span className="font-semibold text-gray-950 text-sm flex items-center">
                    {conv.client_name}
                    {conv.unread && (
                      <span className="w-2 h-2 bg-blue-600 rounded-full ml-2"></span>
                    )}
                  </span>
                  <span className="text-[11px] text-gray-400">{relativeTime(conv.last_message_at, now)}</span>
                </div>
                <p className="text-xs text-gray-500 truncate w-full mb-2">{conv.last_message}</p>
                <div className="flex justify-between items-center w-full">
                  <StatusBadge status={conv.status} small />
                  <span className="text-[10px] text-gray-400 font-mono">{conv.phone_number}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right Side: Conversation Thread */}
        {activeConv ? (
          <Thread key={activeConv.client_id} conversation={activeConv} timeZone={business?.timezone} />
        ) : (
          <div className="flex-1 bg-slate-50" />
        )}
      </div>
    </div>
  );
}

function Thread({ conversation, timeZone }: { conversation: Conversation; timeZone?: string }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const id = conversation.client_id;

  const { data: messages = [] } = useQuery({
    queryKey: ['messages', id],
    queryFn: async () => (await api.get<Message[]>(`/conversations/${id}/messages`)).data,
    refetchInterval: 5_000,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages.length]);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['messages', id] });
    queryClient.invalidateQueries({ queryKey: ['conversations'] });
    queryClient.invalidateQueries({ queryKey: ['clients'] });
  };

  const toggleAi = useMutation({
    mutationFn: () => api.post(`/conversations/${id}/${conversation.ai_paused ? 'resume' : 'pause'}`),
    onSuccess: refresh,
  });
  const send = useMutation({
    mutationFn: (body: string) => api.post(`/conversations/${id}/messages`, { body }),
    onSuccess: () => {
      setDraft('');
      refresh();
    },
    onError: refresh, // the failed attempt is logged and shown in the thread
  });

  const optedOut = conversation.status === 'opted_out';

  return (
    <div className="flex-1 flex flex-col bg-slate-50 h-full min-w-0">
      {/* Active Header */}
      <div className="p-4 bg-white border-b border-gray-100 flex-shrink-0 flex items-center justify-between">
        <div className="flex items-center">
          <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center font-bold text-gray-600 text-sm mr-3">
            {initials(conversation.client_name)}
          </div>
          <div>
            <h3 className="font-bold text-gray-900 text-sm">{conversation.client_name}</h3>
            <p className="text-xs text-gray-500 flex items-center mt-0.5">
              <Phone className="w-3 h-3 mr-1" />
              {conversation.phone_number}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {conversation.ai_paused ? (
            <button
              onClick={() => toggleAi.mutate()}
              disabled={toggleAi.isPending}
              className="text-xs bg-green-50 text-green-700 border border-green-200 px-3 py-1.5 rounded-lg font-medium hover:bg-green-100 transition-colors"
            >
              Resume AI Agent
            </button>
          ) : (
            <>
              <button
                onClick={() => toggleAi.mutate()}
                disabled={toggleAi.isPending}
                className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-3 py-1.5 rounded-lg font-medium hover:bg-amber-100 transition-colors"
              >
                Pause AI Agent
              </button>
              <button
                onClick={() => toggleAi.mutate(undefined, { onSuccess: () => inputRef.current?.focus() })}
                disabled={toggleAi.isPending}
                className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Take Over Chat
              </button>
            </>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 p-6 overflow-y-auto space-y-4">
        {messages.map((msg) => {
          if (msg.sender === 'system') {
            return (
              <p key={msg.id} className="text-center text-[11px] text-gray-500 bg-gray-100 rounded-lg px-3 py-1.5 mx-auto w-fit max-w-md">
                {msg.message_body}
              </p>
            );
          }
          const outbound = msg.direction === 'outbound';
          return (
            <div key={msg.id} className={`flex ${outbound ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-md rounded-xl p-3.5 shadow-sm text-sm ${
                outbound
                  ? 'bg-green-600 text-white rounded-tr-none'
                  : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
              } ${msg.status === 'failed' ? 'opacity-70 ring-2 ring-red-400' : ''}`}>
                {outbound && (
                  <div className="flex items-center gap-1 text-[10px] font-semibold text-green-100 uppercase tracking-wide mb-1.5">
                    {msg.sender === 'ai' ? <Sparkles className="w-3 h-3" /> : <UserRound className="w-3 h-3" />}
                    {msg.sender === 'ai' ? 'AI Scheduler Assistant' : 'You'}
                  </div>
                )}
                <p className="leading-relaxed whitespace-pre-wrap">{msg.message_body}</p>
                <span className={`text-[10px] block text-right mt-1.5 ${outbound ? 'text-green-200' : 'text-gray-400'}`}>
                  {msg.status === 'failed' ? `Not delivered: ${msg.error ?? 'error'}` : formatTime(msg.timestamp, timeZone)}
                </span>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Manual reply; sending pauses the AI for this client */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (draft.trim()) send.mutate(draft.trim());
        }}
        className="p-4 bg-white border-t border-gray-100 flex-shrink-0"
      >
        {send.isError && <p className="mb-2 text-xs text-red-600">{errorMessage(send.error)}</p>}
        <div className="flex items-center gap-3">
          <input
            ref={inputRef}
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              optedOut
                ? 'This client opted out of messages'
                : conversation.ai_paused
                  ? 'Reply manually...'
                  : 'Type a message to take over and reply manually...'
            }
            disabled={optedOut}
            className="flex-1 p-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={optedOut || !draft.trim() || send.isPending}
            className="bg-blue-600 text-white p-2.5 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
            aria-label="Send"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
