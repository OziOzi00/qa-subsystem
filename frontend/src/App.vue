<template>
  <main class="qa-page">
    <header class="qa-header">
      <div>
        <p class="eyebrow">Overseas Chinese Cultural Relics</p>
        <h1>文物知识问答</h1>
      </div>
      <div class="session-chip" title="当前问答会话标识">
        {{ sessionId }}
      </div>
    </header>

    <section class="qa-shell" aria-label="知识问答">
      <aside class="qa-sidebar">
        <label class="field-label" for="objectIdInput">当前文物 objectId</label>
        <div class="object-row">
          <input
            id="objectIdInput"
            v-model.trim="objectId"
            type="text"
            placeholder="例如 DEMO_001"
            @keyup.enter="sendMessage()"
          />
          <button class="ghost-btn" type="button" @click="useDemoObject">
            演示
          </button>
          <button class="ghost-btn" type="button" @click="resetSession">
            新会话
          </button>
        </div>
        <p class="hint">支持从 URL 读取 objectId，也可单独演示时手动输入；新会话会清空当前文物上下文。</p>

        <div class="example-list">
          <button
            v-for="example in exampleQuestions"
            :key="example"
            type="button"
            @click="sendQuestion(example)"
          >
            {{ example }}
          </button>
        </div>
      </aside>

      <section class="chat-panel">
        <div ref="chatMessages" class="chat-messages">
          <div v-if="messages.length === 0" class="welcome-message">
            <h2>请选择文物或直接提问</h2>
            <p>系统会展示答案、事实内容、补充说明、数据来源和相关文物推荐。</p>
          </div>

          <article
            v-for="message in messages"
            :key="message.id"
            :class="['message', message.type]"
          >
            <div class="message-content">
              <template v-if="message.type === 'user'">
                <p>{{ message.content }}</p>
                <span v-if="message.objectId" class="message-meta">
                  objectId: {{ message.objectId }}
                </span>
              </template>

              <template v-else>
                <div :class="['status-badge', message.status]">
                  {{ getStatusText(message.status) }}
                </div>
                <p class="answer">{{ message.answer }}</p>

                <section v-if="message.factContent" class="info-block fact">
                  <h3>事实内容</h3>
                  <p>{{ message.factContent }}</p>
                </section>

                <section v-if="message.supplementalContent" class="info-block supplement">
                  <h3>补充说明</h3>
                  <p>{{ message.supplementalContent }}</p>
                </section>

                <section v-if="message.candidates.length" class="choice-block">
                  <h3>请选择文物</h3>
                  <button
                    v-for="candidate in message.candidates"
                    :key="candidate.objectId"
                    :class="['candidate-item', { selected: selectedObjectId === candidate.objectId }]"
                    type="button"
                    @click="selectedObjectId = candidate.objectId"
                  >
                    <span class="candidate-main">
                      <strong>{{ candidate.title || candidate.objectId }}</strong>
                      <small>objectId: {{ candidate.objectId }}</small>
                    </span>
                    <span class="candidate-meta">
                      <small v-if="candidate.museumName">馆藏：{{ candidate.museumName }}</small>
                      <small v-if="candidate.dynastyName">朝代：{{ candidate.dynastyName }}</small>
                      <small v-if="candidate.artifactType">类型：{{ candidate.artifactType }}</small>
                      <a
                        v-if="candidate.detailUrl"
                        :href="candidate.detailUrl"
                        target="_blank"
                        rel="noreferrer"
                        @click.stop
                      >
                        详情页
                      </a>
                    </span>
                  </button>
                  <button
                    class="primary-inline"
                    type="button"
                    :disabled="!selectedObjectId"
                    @click="confirmCandidate(message)"
                  >
                    确认选择并重新提问
                  </button>
                </section>

                <section v-if="message.sources.length" class="sources-section">
                  <h3>数据来源</h3>
                  <div
                    v-for="(source, index) in message.sources"
                    :key="`${source.sourceType}-${index}`"
                    class="source-item"
                  >
                    <div class="source-header">
                      <span :class="['source-type', source.sourceType]">
                        {{ getSourceTypeText(source.sourceType) }}
                      </span>
                      <strong>{{ source.sourceName }}</strong>
                    </div>
                    <p v-if="source.factText">{{ source.factText }}</p>
                    <a
                      v-if="source.detailUrl"
                      :href="source.detailUrl"
                      target="_blank"
                      rel="noreferrer"
                    >
                      查看原始详情页
                    </a>
                  </div>
                </section>

                <section v-if="message.relatedArtifacts.length" class="related-section">
                  <h3>相关文物推荐</h3>
                  <div class="related-grid">
                    <button
                      v-for="artifact in message.relatedArtifacts"
                      :key="artifact.objectId"
                      type="button"
                      @click="loadArtifactContext(artifact.objectId, artifact.title)"
                    >
                      <strong>{{ artifact.title }}</strong>
                      <span>{{ artifact.reason || artifact.objectId }}</span>
                    </button>
                  </div>
                </section>

                <div v-if="message.needFeedback && !message.feedbackSubmitted" class="feedback-section">
                  <button type="button" @click="submitFeedback(message, 'helpful')">
                    有帮助
                  </button>
                  <button type="button" @click="submitFeedback(message, 'inaccurate')">
                    不准确
                  </button>
                </div>

                <p v-if="message.feedbackSubmitted" class="feedback-success">
                  感谢反馈，系统已记录。
                </p>
                <p v-if="message.feedbackError" class="feedback-error">
                  {{ message.feedbackError }}
                </p>
              </template>
            </div>
          </article>

          <div v-if="isLoading" class="loading-row">
            <span class="spinner" />
            <span>正在检索知识库...</span>
          </div>
        </div>

        <form class="input-bar" @submit.prevent="sendMessage()">
          <input
            v-model.trim="question"
            type="text"
            placeholder="请输入您的问题，例如：它的尺寸是多少？"
            :disabled="isLoading"
          />
          <button type="submit" :disabled="!question || isLoading">
            发送
          </button>
        </form>
      </section>
    </section>
  </main>
</template>

<script setup>
import { nextTick, ref } from 'vue';
import axios from 'axios';

const SESSION_KEY = 'qa-web-session-id';
const sessionId = ref(getOrCreateSessionId());

const question = ref('');
const objectId = ref('');
const messages = ref([]);
const isLoading = ref(false);
const selectedObjectId = ref(null);
const chatMessages = ref(null);
const lastClarificationQuestion = ref('');

const exampleQuestions = [
  '演示文物的材质是什么？',
  '介绍一下犀牛角杯',
  '它的尺寸是多少？',
  '这件文物收藏在哪里？',
  'The Metropolitan Museum of Art 收藏了多少件中国文物？',
  '收藏容器最多的博物馆是哪个？',
  '推荐相关文物'
];

function getOrCreateSessionId() {
  const existing = window.localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = createSessionId();
  window.localStorage.setItem(SESSION_KEY, created);
  return created;
}

function createSessionId() {
  return `qa-web-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function getStatusText(status) {
  const statusMap = {
    answered: '已回答',
    no_data: '暂无数据',
    need_clarification: '需要确认',
    unsupported: '暂不支持',
    error: '系统错误'
  };
  return statusMap[status] || status;
}

function getSourceTypeText(type) {
  const typeMap = {
    mysql: 'MySQL',
    neo4j: 'Neo4j',
    template: '演示数据',
    llm: 'AI 补充'
  };
  return typeMap[type] || type;
}

function useDemoObject() {
  objectId.value = 'DEMO_001';
}

function resetSession() {
  const created = createSessionId();
  window.localStorage.setItem(SESSION_KEY, created);
  sessionId.value = created;
  question.value = '';
  objectId.value = '';
  messages.value = [];
  selectedObjectId.value = null;
  lastClarificationQuestion.value = '';

  const cleanUrl = `${window.location.pathname}${window.location.hash || ''}`;
  window.history.replaceState({}, '', cleanUrl);
}

function sendQuestion(text) {
  question.value = text;
  sendMessage();
}

async function sendMessage(overrideQuestion = null) {
  const currentQuestion = (overrideQuestion || question.value).trim();
  if (!currentQuestion || isLoading.value) return;

  messages.value.push({
    id: crypto.randomUUID(),
    type: 'user',
    content: currentQuestion,
    objectId: objectId.value || null
  });
  selectedObjectId.value = null;
  await scrollToBottom();

  isLoading.value = true;
  try {
    const response = await axios.post('/api/qa/ask', {
      question: currentQuestion,
      objectId: objectId.value || undefined,
      sessionId: sessionId.value,
      sourceClient: 'web'
    });

    const data = response.data;
    if (data.status === 'need_clarification') {
      lastClarificationQuestion.value = currentQuestion;
    }
    if (data.resolvedObject?.objectId) {
      objectId.value = data.resolvedObject.objectId;
    }

    messages.value.push({
      id: crypto.randomUUID(),
      type: 'bot',
      qaLogId: data.qaLogId,
      status: data.status,
      intent: data.intent,
      answer: data.answer,
      factContent: data.factContent,
      supplementalContent: data.supplementalContent,
      resolvedObject: data.resolvedObject,
      candidates: data.resolvedObject?.candidates || [],
      sources: data.sources || [],
      relatedArtifacts: data.relatedArtifacts || [],
      needFeedback: data.needFeedback || false,
      feedbackSubmitted: false,
      feedbackError: ''
    });
  } catch (error) {
    messages.value.push({
      id: crypto.randomUUID(),
      type: 'bot',
      status: 'error',
      answer: error.response?.data?.detail || '抱歉，系统暂时无法处理您的请求。请稍后重试。',
      factContent: null,
      supplementalContent: null,
      candidates: [],
      sources: [],
      relatedArtifacts: [],
      needFeedback: false,
      feedbackSubmitted: false,
      feedbackError: ''
    });
  } finally {
    isLoading.value = false;
    question.value = '';
    await scrollToBottom();
  }
}

function confirmCandidate(message) {
  if (!selectedObjectId.value) return;
  objectId.value = selectedObjectId.value;
  const retryQuestion = lastClarificationQuestion.value || message.answer || '介绍一下这件文物';
  sendMessage(retryQuestion);
}

function loadArtifactContext(nextObjectId, title) {
  objectId.value = nextObjectId;
  sendMessage(`介绍一下${title || '这件文物'}`);
}

async function submitFeedback(message, feedbackType) {
  try {
    await axios.post('/api/qa/feedback', {
      qaLogId: message.qaLogId,
      feedbackType,
      sourceClient: 'web'
    });
    message.feedbackSubmitted = true;
    message.feedbackError = '';
  } catch (error) {
    message.feedbackError = error.response?.data?.detail || '反馈提交失败，请稍后重试。';
  }
}

async function scrollToBottom() {
  await nextTick();
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight;
  }
}

function parseUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const idFromUrl = params.get('objectId') || params.get('object_id');
  if (idFromUrl) {
    objectId.value = idFromUrl;
  }
}

parseUrlParams();
</script>
