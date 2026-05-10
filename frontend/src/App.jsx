//======================================================================
//======================================================================
// 메인 화면
//======================================================================
//======================================================================

import { Routes, Route, Link, Outlet, useNavigate } from 'react-router-dom';
import Info from './Info';
import About from './About';
import Login from './Login'; 
import Register from './Register'; 
import simbol from './assets/simbol.png';
import Search from './Search';
import MyPage from './Mypage';
import mainBanner from './assets/main_banner.jpg';
import './App.css';
import { useAuth } from './AuthContext'; 
import React, { useState, useEffect } from 'react';
import http from './api/http'; 
import BoardPage from './BoardPage';
import NoticeDetailPage from './NoticeDetailPage';


function HomePage() {
  const [notices, setNotices] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [keyword, setKeyword] = useState(''); 
  const navigate = useNavigate(); 

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

  const handleMainSearch = (e) => {
    e.preventDefault(); 
    if (keyword.trim()) {
      navigate(`/search?search=${keyword}`);
    }
  };

  
  const renderNoticeList = () => {
    if (loading) {
      return <li><a href="#">- 공지사항을 불러오는 중...</a></li>;
    }

    if (error) {
      return <li><a href="#">- 공지 로딩 중 오류 발생</a></li>;
    }

    if (notices?.length > 0) {
      return notices.map(notice => (
        <li 
          key={notice.notice_id} 
          style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '8px'
          }}
        > 
          <Link 
            to={`/notice/${notice.notice_id}`}
            style={{ 
              textDecoration: 'none', 
              color: '#333',
              overflow: 'hidden', 
              textOverflow: 'ellipsis', 
              whiteSpace: 'nowrap' 
            }}
            title={notice.title} 
          >
            - {notice.title}
          </Link>
          <span style={{ 
            fontSize: '0.9rem', 
            color: '#666', 
            marginLeft: '10px', 
            flexShrink: 0 
          }}>
            {new Date(notice.post_date).toLocaleDateString()}
          </span>
        </li>
      ));
    }
    
    return <li><a href="#">- 등록된 공지가 없습니다.</a></li>;
  };

  return ( 
    <>
      <div className="hero-section">
        <img src={mainBanner} alt="메인 배너 이미지" className="main-banner-image" />
        
        <section className="search-section" aria-label="Search Section">
          <form className="search-container" role="search" onSubmit={handleMainSearch}>
            <label htmlFor="search-input" className="visually-hidden">자료 검색</label>
            <input 
              type="search" 
              id="search-input" 
              className="rectangle-3" 
              placeholder="자료 검색" 
              value={keyword} 
              onChange={(e) => setKeyword(e.target.value)} 
            />
            
            <button className="rectangle-4" type="submit" aria-label="검색">
              <span className="visually-hidden">검색</span>
            </button>
          </form>
        </section>
      </div>

      <main className="main-content">
        <section className="content-sections">
          <article className="notice-section" aria-labelledby="notice-heading">
            <h2 id="notice-heading">공지 사항</h2>
            <div className="img"></div>
            <ul id="notice-list" className="info-list">
              
              {renderNoticeList()}

            </ul>
          </article>
        </section>
      </main>
    </>
  );
}

function Layout() {
  const { isLoggedIn, user, logout } = useAuth();
  const navigate = useNavigate();
  const handleLogout = (e) => {
    e.preventDefault(); 
    logout();      
    navigate('/'); 
  };

  return (
    <div className="desktop">
      <header className="header">
        <div className="header-top">
          <nav className="utility-nav" aria-label="Utility Navigation">
            <a href="https://deutsch.hufs.ac.kr/sites/deutsch/index.do">독일어과 home</a>
            <a href="https://www.hufs.ac.kr/sites/hufs/index.do">HUFS home</a>
            
            {isLoggedIn ? (
              <>
                <Link to="/mypage" style={{marginRight: '5px'}}>{user?.name}님</Link> / 
                <a href="#!" onClick={handleLogout} style={{marginLeft: '5px', cursor: 'pointer'}}>로그아웃</a>
              </>
            ) : (
              <>
                <Link to="/login">로그인</Link> / <Link to="/register">회원가입</Link>
              </>
            )}
          </nav>
        </div>
        <div className="header-main">
          <Link to="/" className="site-title">
            <img src={simbol} alt="오스트리아 도서관 로고" className="logo-image" />
            <p className="austrian-library">
              Austrian Library<br />Österreichische Bibliothek<br />한국외국어대학교 <strong>오스트리아 도서관</strong>
            </p>
          </Link>
          <nav className="main-nav" aria-label="Main Navigation">
            <Link to="/search">자료 검색</Link>
            <Link to="/board">공지 사항</Link>
            <Link to="/mypage">내 서재</Link>
            <Link to="/info">도서관 안내</Link>
            <Link to="/about">도서관 소개</Link>
          </nav>
        </div>
      </header>
          

      <Outlet /> 
      <footer className="footer">
        <div className="footer-content">
          <address className="element">
            <strong>주소</strong><br />
            02450 서울특별시 동대문구 이문로 107 한국외국어대학교 서울캠퍼스 본관 301호<br />
            서양어대학 독일어과 오스트리아도서관<br /><br />
            <strong>TEL.</strong> 02-2173-2283<br />
            <strong>Email.</strong> deutsch@hufs.ac.kr
          </address>
          <div className="element operating-hours">
            <strong>운영 시간</strong><br />
            학기 중 09:00~17:00<br />
            방학 중 10:00~15:00<br />
            점심시간 12:00~13:00
          </div>
          <div className="element-developer">
            <strong>홈페이지 개발자 정보</strong><br />독일어('24) jsjang0104@naver.com
          </div>
        </div>
      </footer>
    </div>
  );
}

// 경로별 링크
function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="search" element={<Search />} />
        <Route path="mypage" element={<MyPage />} />
        <Route path="board" element={<BoardPage />} />
        <Route path="notice/:noticeId" element={<NoticeDetailPage />} />
        <Route path="info" element={<Info />} />
        <Route path="about" element={<About />} />
        <Route path="login" element={<Login />} /> 
        <Route path="register" element={<Register />} />
      </Route>
    </Routes>
  );
}

export default App;