//======================================================================
//======================================================================
// 공지사항 상세
//======================================================================
//======================================================================
import React, { useState, useEffect } from 'react';
import http from './api/http';
import { useParams, Link } from 'react-router-dom';

function NoticeDetailPage() {
  const { noticeId } = useParams();
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchNoticeDetail = async () => {
      try {
        setNotice(null);
        setError(null);
        setLoading(true);

        const response = await http.get(`/api/notices/${noticeId}/`);
        
        setNotice(response.data);
      } catch (e) {
        setError(e);
      }
      setLoading(false);
    };

    fetchNoticeDetail();
  }, [noticeId]); 

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

  if (!notice) {
    return (
      <main className="main-content about-page">
        <br /><br /><h1>공지</h1>
        <div className="about-section">
          <p>해당 공지사항을 찾을 수 없습니다.</p>
          <Link to="/board">목록으로 돌아가기</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="main-content about-page">
      <br /><br />
      
      <h1>{notice.title}</h1>

      <div className="about-section">
        
        <div style={{ 
          fontSize: '0.9rem', 
          color: '#666',
          paddingBottom: '16px', 
          marginBottom: '24px', 
          borderBottom: '1px solid #eee' 
        }}>
          <span style={{ marginRight: '12px' }}>
            작성자: 도서관
          </span>
          <span style={{ marginRight: '12px' }}>
            작성일: {new Date(notice.post_date).toLocaleDateString()}
          </span>
          <span>
            조회수: {notice.view_count}
          </span>
        </div>

        <div 
          className="notice-content"
          style={{ 
            minHeight: '200px', 
            lineHeight: '1.6', 
            fontSize: '1rem',
            whiteSpace: 'pre-wrap' 
          }}
        >
          {notice.content}
        </div>

        <div style={{ textAlign: 'center', marginTop: '40px' }}>
          <Link 
            to="/board" 
            style={{ 
              padding: '10px 20px', 
              backgroundColor: '#f0f0f0', 
              color: '#333',
              textDecoration: 'none',
              borderRadius: '5px'
            }}
          >
            목록으로
          </Link>
        </div>

      </div>
    </main>
  );
}

export default NoticeDetailPage;