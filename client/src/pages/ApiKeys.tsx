import React, { useEffect, useState } from 'react';
import { request } from '../services/api';

const ApiKeys: React.FC = () => {
  const [keys, setKeys] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [newKey, setNewKey] = useState<string | null>(null);

  const loadKeys = () => {
    request('/users/keys')
      .then(setKeys)
      .catch(err => setError(err.message));
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;
    try {
      const data = await request('/users/keys', {
        method: 'POST',
        body: JSON.stringify({ name })
      });
      setNewKey(data.key);
      setName('');
      loadKeys();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!window.confirm('정말 이 키를 삭제하시겠습니까?')) return;
    try {
      await request(`/users/keys/${keyId}`, { method: 'DELETE' });
      loadKeys();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div>
      <h2>API 키 관리</h2>
      {error && <div className="error mb-1">{error}</div>}
      
      {newKey && (
        <div className="card" style={{ backgroundColor: '#e8f5e9', borderColor: 'var(--success-color)' }}>
          <strong>새로운 API 키가 발급되었습니다!</strong> 지금 즉시 복사해 두세요. 다시 확인할 수 없습니다.
          <pre>{newKey}</pre>
          <button onClick={() => setNewKey(null)}>닫기</button>
        </div>
      )}

      <form onSubmit={handleCreate} className="flex gap-1 mb-2 align-center">
        <input value={name} onChange={e => setName(e.target.value)} placeholder="키 이름" required />
        <button type="submit">키 생성</button>
      </form>

      <table>
        <thead>
          <tr>
            <th>이름</th>
            <th>키 식별자</th>
            <th>생성 일시</th>
            <th>액션</th>
          </tr>
        </thead>
        <tbody>
          {keys.map(k => (
            <tr key={k.id}>
              <td>{k.name}</td>
              <td>{k.maskedKey}</td>
              <td>{new Date(k.createdAt).toLocaleString()}</td>
              <td>
                <button onClick={() => handleDelete(k.id)}>삭제</button>
              </td>
            </tr>
          ))}
          {keys.length === 0 && (
            <tr><td colSpan={4}>생성된 API 키가 없습니다.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default ApiKeys;
