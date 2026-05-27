import React from 'react';

const ApiDocs: React.FC = () => {
  return (
    <div>
      <h2>API 연동 문서</h2>
      <p>발급받은 API 키를 사용하여 고객님의 애플리케이션에 악성 프롬프트 탐지 서비스를 연동해 보세요.</p>
      
      <h3>엔드포인트 (Endpoint)</h3>
      <pre>POST /api/v1/analyze</pre>

      <h3>헤더 (Headers)</h3>
      <table>
        <thead>
          <tr>
            <th>헤더</th>
            <th>값 (Value)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>X-API-Key</td>
            <td>발급받은 API 키</td>
          </tr>
          <tr>
            <td>Content-Type</td>
            <td>application/json</td>
          </tr>
        </tbody>
      </table>

      <h3>요청 바디 (Request Body)</h3>
      <pre>
{`{
  "prompt": "string"
}`}
      </pre>

      <h3>예제: cURL</h3>
      <pre>
{`curl -X POST http://localhost/api/v1/analyze \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "테스트할 프롬프트 입력"}'`}
      </pre>

      <h3>예제: Python</h3>
      <pre>
{`import requests

url = "http://localhost/api/v1/analyze"
headers = {
    "X-API-Key": "YOUR_API_KEY",
    "Content-Type": "application/json"
}
data = {
    "prompt": "테스트할 프롬프트 입력"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())`}
      </pre>
    </div>
  );
};

export default ApiDocs;
