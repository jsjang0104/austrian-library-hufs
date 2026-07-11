//======================================================================
//======================================================================
// 공지사항
//======================================================================
//======================================================================
import React, { useState, useEffect } from 'react';
import http from './api/http';
import { Link } from 'react-router-dom';

function BoardPage() {
  const [notices, setNotices] = useState(null); 
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchNotices = async () => {
      try {
        setError(null);
        setNotices(null);
        setLoading(true);
        const response = await http.get('/api/notices/');
        setNotices(response.data); 
      } catch (e) {
        setError(e);
      }
      setLoading(false);
    };
    fetchNotices(); 
  }, []); 

  if (loading) {
    return (
      <main className="main-content about-page">
        <br /><br /><h1>공지</h1>
        <div className="about-section">
          <p>공지사항을 불러오는 중입니다...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="main-content about-page">
        <br /><br /><h1>공지</h1>
        <div className="about-section">
          <p>오류가 발생했습니다: {error.message}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="main-content about-page">
      <br /><br />
      <h1>공지</h1>

      <div className="about-section">
        <ul style={{ listStyle: 'none', paddingLeft: '0' }}>
          
          {notices?.length > 0 ? (
            notices.map(notice => (

              <li 
                key={notice.notice_id} 
                style={{ 
                  paddingBottom: '16px', 
                  marginBottom: '16px', 
                  borderBottom: '1px solid #eee' 
                }}
              > 
                
                <div style={{ marginBottom: '8px' }}>
                  <Link 
                    to={`/notice/${notice.notice_id}`}
                    style={{ 
                      fontSize: '1.1rem', 
                      textDecoration: 'none', 
                      color: '#333', 
                      fontWeight: 500
                    }}
                  >
                    {notice.title} 
                  </Link>
                </div>
                <div style={{ fontSize: '0.9rem', color: '#666' }}>
                  <span style={{ marginRight: '12px' }}>
                    작성자: {notice.manager || 'N/A'}
                  </span>

                  <span style={{ marginRight: '12px' }}>
                    작성일: {new Date(notice.post_date).toLocaleDateString()}
                  </span>
                  
                  <span>
                    조회수: {notice.view_count}
                  </span>
                </div>
                
              </li>
            ))
          ) : (
            <li>- 등록된 공지가 없습니다.</li>
          )}
        </ul>
      </div>
    </main>
  );
}

export default BoardPage;