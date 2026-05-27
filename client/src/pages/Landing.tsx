import React, { useState } from 'react';
import { request } from '../services/api';

const Landing: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleTest = async () => {
    if (!prompt) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await request('/v1/analyze/demo', {
        method: 'POST',
        body: JSON.stringify({ prompt, model: 'intfloat/multilingual-e5-small' })
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-col gap-2">
      <h1>악성 프롬프트 탐지 시스템</h1>
      <p>아래에 프롬프트를 입력하여 AI 탐지 모델을 테스트해 보세요.</p>
      
      <div className="flex gap-1">
        <input 
          value={prompt} 
          onChange={(e) => setPrompt(e.target.value)} 
          placeholder="프롬프트를 입력하세요..." 
          style={{ width: '100%', maxWidth: '600px' }}
        />
        <button onClick={handleTest} disabled={loading}>
          {loading ? '테스트 중...' : '프롬프트 테스트'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="card mt-2">
          <h3>테스트 결과</h3>
          <div className="flex gap-2">
            <div><strong>상태:</strong> {result.safe ? <span className="success">안전함 (Safe)</span> : <span className="error">악성 (Malicious)</span>}</div>
            <div><strong>위험도 점수:</strong> {result.score}</div>
            <div><strong>처리 시간:</strong> {result.processingTime}ms</div>
          </div>
          

        </div>
      )}
    </div>
  );
};

export default Landing;
