<template>
  <div class="container">
    <div class="header">
      <h1>🏺 文物知识问答</h1>
      <p>探索海外藏中国文物的奥秘</p>
    </div>

    <div class="chat-container">
      <div class="chat-messages" ref="chatMessages">
        <div v-if="messages.length === 0" class="welcome-message">
          <div style="margin-bottom: 20px;">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="mx-auto mb-4" style="color: #6366f1;">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <h3>欢迎使用文物知识问答系统</h3>
          <p>请输入您的问题，或从下方示例中选择：</p>
          <div class="examples">
            <span 
              v-for="(example, index) in exampleQuestions" 
              :key="index"
              class="example-tag"
              @click="sendQuestion(example)"
            >
              {{ example }}
            </span>
          </div>
        </div>

        <div 
          v-for="(msg, index) in messages" 
          :key="index" 
          :class="['message', msg.type]"
        >
          <div class="message-content">
            <div v-if="msg.type === 'user'">
              <div class="user-message-text">{{ msg.content }}</div>
              <div v-if="msg.objectId" class="user-object-id">
                <span class="object-id-label">文物标识：</span>{{ msg.objectId }}
              </div>
            </div>
            <div v-else-if="msg.type === 'bot'">
              <div :class="['status-badge', msg.status]">
                <span class="status-icon">{{ getStatusIcon(msg.status) }}</span>
                {{ getStatusText(msg.status) }}
              </div>
              
              <div v-if="msg.status === 'need_clarification'" class="answer">
                <span class="clarification-icon">🔍</span> {{ msg.answer }}
              </div>
              <div v-else class="answer">{{ msg.answer }}</div>

              <div v-if="msg.factContent" class="fact-content">
                <div class="fact-label">
                  <span>📌</span>
                  <span>事实内容</span>
                </div>
                {{ msg.factContent }}
              </div>

              <div v-if="msg.supplementalContent" class="supplemental-content">
                <div class="supplemental-label">
                  <span>💡</span>
                  <span>补充说明</span>
                </div>
                {{ msg.supplementalContent }}
              </div>

              <div v-if="msg.candidates && msg.candidates.length > 0" class="candidates-section">
                <div class="candidates-title">
                  <span>🎯</span>
                  <span>请选择文物：</span>
                </div>
                <div 
                  v-for="candidate in msg.candidates" 
                  :key="candidate.objectId"
                  :class="['candidate-item', { selected: selectedObjectId === candidate.objectId }]"
                  @click="selectCandidate(candidate.objectId)"
                >
                  <div class="candidate-radio">
                    <span v-if="selectedObjectId === candidate.objectId" class="radio-selected">✓</span>
                  </div>
                  <span class="candidate-title">{{ candidate.title }}</span>
                  <span class="candidate-confidence">{{ (candidate.confidence * 100).toFixed(0) }}%</span>
                </div>
                <button 
                  v-if="selectedObjectId"
                  class="confirm-candidate-btn"
                  @click="confirmCandidate(msg)"
                >
                  <span>✅</span>
                  <span>确认选择并继续提问</span>
                </button>
              </div>

              <div v-if="msg.sources && msg.sources.length > 0" class="sources-section">
                <div class="sources-title">
                  <span>📚</span>
                  <span>数据来源</span>
                </div>
                <div v-for="(source, idx) in msg.sources" :key="idx" class="source-item">
                  <div class="source-header">
                    <span :class="['source-type', source.sourceType]">{{ getSourceTypeText(source.sourceType) }}</span>
                    <span class="source-name">{{ source.sourceName }}</span>
                  </div>
                  <div v-if="source.factText" class="source-fact">
                    {{ source.factText }}
                  </div>
                  <a v-if="source.detailUrl" :href="source.detailUrl" class="source-url" target="_blank">
                    <span>🔗</span>
                    <span>查看详情</span>
                  </a>
                </div>
              </div>

              <div v-if="msg.relatedArtifacts && msg.relatedArtifacts.length > 0" class="related-artifacts-section">
                <div class="related-title">
                  <span>🎨</span>
                  <span>相关文物推荐</span>
                </div>
                <div class="related-grid">
                  <div 
                    v-for="artifact in msg.relatedArtifacts" 
                    :key="artifact.objectId"
                    class="related-item"
                    @click="loadArtifactContext(artifact.objectId, artifact.title)"
                  >
                    <div class="related-icon">🏛️</div>
                    <div class="related-title-text">{{ artifact.title }}</div>
                    <div class="related-reason">{{ artifact.reason }}</div>
                  </div>
                </div>
              </div>

              <div v-if="msg.needFeedback && !msg.feedbackSubmitted" class="feedback-section">
                <button 
                  class="feedback-btn helpful"
                  @click="submitFeedback(msg.qaLogId, 'helpful')"
                >
                  <span>👍</span>
                  <span>有帮助</span>
                </button>
                <button 
                  class="feedback-btn inaccurate"
                  @click="submitFeedback(msg.qaLogId, 'inaccurate')"
                >
                  <span>👎</span>
                  <span>不准确</span>
                </button>
              </div>

              <div v-if="msg.feedbackSubmitted" class="feedback-success">
                <span>✓</span>
                <span>感谢您的反馈！</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isLoading" class="loading-indicator">
          <div class="spinner"></div>
        </div>
      </div>

      <div class="input-container">
        <div class="input-wrapper">
          <div class="object-id-input">
            <label for="objectIdInput">
              <span class="label-icon">🏺</span>
              <span>文物标识 (objectId) - 可选</span>
            </label>
            <input 
              id="objectIdInput"
              v-model="objectId" 
              type="text" 
              placeholder="例如：DEMO_001"
              @keyup.enter="sendMessage"
            />
          </div>
          <input 
            v-model="question" 
            type="text" 
            placeholder="请输入您的问题..."
            @keyup.enter="sendMessage"
            :disabled="isLoading"
            class="question-input"
          />
        </div>
        <button 
          class="send-btn" 
          @click="sendMessage"
          :disabled="!question.trim() || isLoading"
        >
          <span class="send-icon">→</span>
          <span>发送</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import axios from 'axios';

const question = ref('');
const objectId = ref('');
const messages = ref([]);
const isLoading = ref(false);
const selectedObjectId = ref(null);
const chatMessages = ref(null);

const exampleQuestions = [
  '这件文物收藏在哪里？',
  '演示文物的材质是什么？',
  '这件文物是什么年代的？',
  '这件文物的作者是谁？',
  '还有哪些类似的文物？',
  '这件文物的尺寸是多少？',
  '这件文物的介绍'
];

const getStatusText = (status) => {
  const statusMap = {
    'answered': '已回答',
    'no_data': '暂无数据',
    'need_clarification': '需要确认',
    'unsupported': '暂不支持',
    'error': '系统错误'
  };
  return statusMap[status] || status;
};

const getStatusIcon = (status) => {
  const iconMap = {
    'answered': '✓',
    'no_data': 'ℹ️',
    'need_clarification': '❓',
    'unsupported': '⚠️',
    'error': '✕'
  };
  return iconMap[status] || '•';
};

const getSourceTypeText = (type) => {
  const typeMap = {
    'mysql': 'MySQL',
    'neo4j': 'Neo4j',
    'template': '演示数据',
    'llm': 'AI 生成'
  };
  return typeMap[type] || type;
};

const scrollToBottom = async () => {
  await nextTick();
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight;
  }
};

const sendQuestion = (q) => {
  question.value = q;
  sendMessage();
};

const sendMessage = async () => {
  if (!question.value.trim() || isLoading.value) return;

  const userMessage = {
    type: 'user',
    content: question.value,
    objectId: objectId.value || null
  };
  messages.value.push(userMessage);
  selectedObjectId.value = null;
  
  await scrollToBottom();
  isLoading.value = true;

  try {
    const response = await axios.post('/api/qa/ask', {
      question: question.value,
      objectId: objectId.value || undefined,
      sourceClient: 'web'
    });

    const data = response.data;
    const botMessage = {
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
      feedbackSubmitted: false
    };

    messages.value.push(botMessage);
  } catch (error) {
    const errorMessage = {
      type: 'bot',
      status: 'error',
      answer: '抱歉，系统暂时无法处理您的请求。请稍后重试。',
      factContent: null,
      supplementalContent: null,
      sources: [],
      relatedArtifacts: [],
      needFeedback: false,
      feedbackSubmitted: false
    };
    messages.value.push(errorMessage);
  } finally {
    isLoading.value = false;
    question.value = '';
    await scrollToBottom();
  }
};

const selectCandidate = (objId) => {
  selectedObjectId.value = objId;
};

const confirmCandidate = (msg) => {
  if (!selectedObjectId.value) return;
  
  objectId.value = selectedObjectId.value;
  const selectedCandidate = msg.candidates.find(c => c.objectId === selectedObjectId.value);
  
  const userMessage = {
    type: 'user',
    content: `已选择：${selectedCandidate?.title || selectedObjectId.value}`,
    objectId: selectedObjectId.value
  };
  messages.value.push(userMessage);
  
  sendMessage();
};

const loadArtifactContext = (objId, title) => {
  objectId.value = objId;
  question.value = `介绍一下${title}`;
  sendMessage();
};

const submitFeedback = async (qaLogId, feedbackType) => {
  try {
    await axios.post('/api/qa/feedback', {
      qaLogId: qaLogId,
      feedbackType: feedbackType
    });
    
    const message = messages.value.find(m => m.qaLogId === qaLogId);
    if (message) {
      message.feedbackSubmitted = true;
    }
  } catch (error) {
    console.error('提交反馈失败:', error);
  }
};

const parseUrlParams = () => {
  const params = new URLSearchParams(window.location.search);
  const objId = params.get('objectId');
  if (objId) {
    objectId.value = objId;
  }
};

parseUrlParams();
</script>

<style scoped>
.user-message-text {
  font-size: 1rem;
  line-height: 1.5;
}

.user-object-id {
  margin-top: 8px;
  font-size: 0.82rem;
  opacity: 0.8;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

.object-id-label {
  font-weight: 500;
}

.clarification-icon {
  margin-right: 8px;
}

.candidate-radio {
  width: 24px;
  height: 24px;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  transition: all 0.2s ease;
}

.candidate-item.selected .candidate-radio {
  background: #6366f1;
  border-color: #6366f1;
}

.radio-selected {
  color: white;
  font-size: 0.75rem;
  font-weight: bold;
}

.confirm-candidate-btn {
  width: 100%;
  padding: 14px 20px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
}

.confirm-candidate-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

.source-fact {
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 6px;
}

.label-icon {
  margin-right: 6px;
}

.send-icon {
  font-size: 1.2rem;
}

.question-input {
  padding-right: 20px !important;
}

.related-icon {
  font-size: 1.8rem;
  margin-bottom: 8px;
}

.status-icon {
  font-size: 0.85rem;
}
</style>
