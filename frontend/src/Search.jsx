import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import http from './api/http';
import './App.css';

function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('search') || '';
  const initialAI = searchParams.get('ai') === '1';

  const [keyword, setKeyword] = useState(initialQuery);
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const [aiSearch, setAiSearch] = useState(initialAI);

  const [selectedLang, setSelectedLang] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedBookId, setExpandedBookId] = useState(null);
  const PAGE_SIZE = 10;
  const STATUS_MAP = {
    'AVAILABLE': '대출 가능', 'available': '대출 가능',
    'ON_LOAN': '대출 중',     'loaned': '대출 중',
    'LOST': '분실',          'lost': '분실'
  };

  const LANG_MAP = {
    'KR': '한국어', 'Korean': '한국어',
    'DE': '독일어', 'Deutsch': '독일어',
    'EN': '영어',   'English': '영어',
    'ETC': '기타'
  };

  const clean = (params) =>
    Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== ''));

  const fetchBooks = async (searchKeyword, useAI) => {
    try {
      setLoading(true);
      const filters = {
        language: selectedLang,
        category: selectedCategory,
        status: selectedStatus
      };

      const response = searchKeyword && useAI
        ? await http.get('/api/books/smart_search/', {
            params: clean({ q: searchKeyword, ...filters })
          })
        : await http.get('/api/books/', {
            params: clean({ search: searchKeyword, ...filters })
          });

      setBooks(response.data);
      setSearched(true);
      setCurrentPage(1);
      setExpandedBookId(null);

    } catch (error) {
      console.error("검색 실패:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuery) fetchBooks(initialQuery, initialAI);
  }, []);

  useEffect(() => {
    if (searched || keyword || selectedLang || selectedCategory || selectedStatus) {
      fetchBooks(keyword, aiSearch);
    }
  }, [selectedLang, selectedCategory, selectedStatus]);

  const handleSearch = (e) => {
    e.preventDefault();
    setAiSearch(false);
    setSearchParams({ search: keyword });
    fetchBooks(keyword, false);
  };

  const handleAISearch = () => {
    setAiSearch(true);
    if (keyword.trim()) fetchBooks(keyword, true);
  };

  const goToPage = (page) => {
    setExpandedBookId(null);
    setCurrentPage(page);
  };

  const toggleRow = (bookId) => {
    setExpandedBookId((prev) => (prev === bookId ? null : bookId));
  };

  const renderBookDetail = (book) => {
    const hasTranslation = Boolean(book.translated_title || book.translated_author);
    const hasSearchText = Boolean(book.search_text);

    if (!hasTranslation && !hasSearchText) {
      return <p className="book-detail-empty">등록된 추가 정보가 없습니다.</p>;
    }

    const translationParts = [
      book.translated_title && `제목 번역: ${book.translated_title}`,
      book.translated_author && `저자 번역: ${book.translated_author}`
    ].filter(Boolean);

    return (
      <>
        <span className="book-detail-caption">✦ AI 생성 정보입니다</span>
        {translationParts.length > 0 && (
          <p className="book-detail-translation">{translationParts.join(' · ')}</p>
        )}
        {hasSearchText && <p className="book-detail-text">{book.search_text}</p>}
      </>
    );
  };

  return (
    <main className="main-content info-page">
      <br /><br />
      <h1>자료 검색</h1>

      <div className="info-section search-wrapper">
        <form onSubmit={handleSearch} className="library-search-form">

          <div className="search-row">
            <input 
              type="text" 
              placeholder="도서명, 저자, 청구기호 등을 입력하세요" 
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              className="search-input-lg"
            />
            <button type="submit" className="search-btn-lg">검색</button>
            <button
              type="button"
              className={`ai-search-btn${aiSearch ? ' active' : ''}`}
              onClick={handleAISearch}
              title="AI 검색 모드: 의미 기반 하이브리드 검색을 사용합니다 (몇 초 정도 걸릴 수 있어요)"
            >
              ✦ AI 검색
            </button>
          </div>

          <div className="filter-group">
            <select 
              value={selectedLang} 
              onChange={(e) => setSelectedLang(e.target.value)}
              className="search-input-lg"
            >
              <option value="">-- 언어 전체 --</option>
              <option value="DE">독일어</option>
              <option value="KR">한국어</option>
              <option value="EN">영어</option>
              <option value="ETC">기타</option>
            </select>

            <select 
              value={selectedCategory} 
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="search-input-lg"
            >
              <option value="">-- 분야 전체 --</option>
              <option value="문학">문학</option>
              <option value="어학">어학</option>
              <option value="역사">역사</option>
              <option value="사회과학">사회과학</option>
              <option value="기타">기타</option>
            </select>

            <select 
              value={selectedStatus} 
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="search-input-lg"
            >
              <option value="">-- 상태 전체 --</option>
              <option value="AVAILABLE">대출 가능</option>
              <option value="ON_LOAN">대출 중</option>
              <option value="LOST">분실</option>
            </select>
          </div>

        </form>
      </div>

      <div className="info-section">
        <h2>검색 결과</h2>
        {loading ? (
          <p className="loading-msg">{aiSearch ? 'AI가 도서를 찾고 있어요' : '데이터를 불러오는 중입니다...'}</p>
        ) : (
          <>
            <div className="table-container">
              <table className="library-table">
                <thead>
                  <tr>
                    <th width="15%">청구기호</th>
                    <th width="30%">제목</th>
                    <th width="15%">저자</th>
                    <th width="10%">언어</th>
                    <th width="10%">분야</th>
                    <th width="10%">위치</th>
                    <th width="10%">상태</th>
                  </tr>
                </thead>
                <tbody>
                  {books && books.length > 0 ? (
                    books.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE).map((book) => {
                      const bookId = book.id || book.book_id;
                      const isExpanded = expandedBookId === bookId;
                      return (
                        <React.Fragment key={bookId}>
                          <tr
                            className="book-row"
                            onClick={() => toggleRow(bookId)}
                            aria-expanded={isExpanded}
                          >
                            <td>{book.call_number}</td>
                            <td className="text-left">{book.title}</td>
                            <td>{book.author || '-'}</td>
                            <td>{LANG_MAP[book.language] || book.language}</td>
                            <td>{book.category}</td>
                            <td>{book.location || '-'}</td>
                            <td>
                              <span className={`status-badge ${
                                (book.status === 'AVAILABLE' || book.status === 'available')
                                ? 'available' : 'borrowed'
                              }`}>
                                {STATUS_MAP[book.status] || book.status}
                              </span>
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr className="book-detail-row">
                              <td colSpan="7" className="book-detail-cell">
                                {renderBookDetail(book)}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="7" className="no-result">
                        {searched ? "검색 결과가 없습니다." : "검색어를 입력해 주세요."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {books.length > PAGE_SIZE && (() => {
              const totalPages = Math.ceil(books.length / PAGE_SIZE);
              const delta = 2;
              const pages = [];
              const range = [];
              for (let i = Math.max(2, currentPage - delta); i <= Math.min(totalPages - 1, currentPage + delta); i++) {
                range.push(i);
              }
              pages.push(1);
              if (range[0] > 2) pages.push('...');
              pages.push(...range);
              if (range[range.length - 1] < totalPages - 1) pages.push('...');
              if (totalPages > 1) pages.push(totalPages);

              return (
                <div className="pagination">
                  <button
                    className="page-btn"
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    &lt;
                  </button>
                  {pages.map((page, idx) =>
                    page === '...' ? (
                      <span key={`ellipsis-${idx}`} className="page-ellipsis">...</span>
                    ) : (
                      <button
                        key={page}
                        className={`page-btn ${currentPage === page ? 'active' : ''}`}
                        onClick={() => goToPage(page)}
                      >
                        {page}
                      </button>
                    )
                  )}
                  <button
                    className="page-btn"
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    &gt;
                  </button>
                </div>
              );
            })()}
          </>
        )}
      </div>
    </main>
  );
}

export default Search;