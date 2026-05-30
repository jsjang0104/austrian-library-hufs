//======================================================================
//======================================================================
// 도서관 안내 (완료)
//======================================================================
//======================================================================

import React from 'react';
import locationGif from './assets/location.gif';

function Info() {
  return (
    <main className="main-content info-page">
      <br /><br /><h1>도서관 안내</h1>
      <div className="about-section">
        <h2>도서관 소개</h2>
        <p>한국외국어대학교 서양어대학 독일어과 소속 오스트리아도서관 (Austrian Library, Österreichische Bibliothek)은 1982년 오스트리아 대사관으로부터 직접 독일어 서적 수천 권을 기증받으며 그 역사가 시작되었습니다.
          현재는 총 10,000여권 규모 서적으로 이루어진, 국내에 몇 안 되는 <strong>독일어권 어문학 전문 도서관</strong>입니다.
          <br />
          국내에서 쉬이 접할 수 없는 독일어 서적을 비치해놓음으로서 독일어권 문학,어학에 관한 한국외국어대학교 학생 및 교수님들의 학문 연구 증진에 기여하고 있습니다.
        </p>
      </div>
      <div className="info-section">
        <h2>이용 시간</h2>
        <p><strong>학기 중:</strong> 09:00 ~ 17:00</p>
        <p><strong>방학 중:</strong> 10:00 ~ 15:00</p>
        <p><strong>점심시간:</strong> 12:00 ~ 13:00</p>
        <p>※ 주말 및 공휴일은 휴관입니다.</p>
      </div>
      <div className="info-section">
        <h2>위치 안내</h2>
        <p>서울특별시 02450 동대문구 이문로 107 한국외국어대학교 서울캠퍼스 본관 301호</p>
        <p>Austrian Library, Hankuk University of Foreign Studies, 107, Imun-ro, Dongdaemun-gu, Seoul, 02450, Republic of Korea</p>
        <img src={locationGif} alt="도서관 위치 안내" style={{ marginTop: '20px', maxWidth: '100%' }} />
      </div>
      <div className="info-section">
        <h2>규정</h2>
        <p><strong>대출 방법</strong></p>
        <p>대출 및 반납은 오스트리아 도서관을 직접 방문해주세요.</p>
        <p>본 홈페이지를 통해 도서 조회, 대출 현황 조회가 가능합니다.</p>
        <p>도서 대출 예약은 불가능합니다.</p>
        <br />
        <p><strong>대출 가능 권수 및 기한</strong></p>
        <p>전임교수, 비전임교수: 15권 (3개월)</p>
        <p>대학원생: 10권 (1개월)</p>
        <p>학부생, 졸업생: 5권 (2주)</p>
        <br />
        <p><strong>기증 안내</strong></p>
        <p>도서 기증 문의: 독일어과 학과장실 이메일 (deutsch@hufs.ac.kr)에 하단 내용을 기입하여 문의 부탁드립니다.</p>
        <p>1. 성함, 신분, 연락처</p>
        <p>2. 도서 권종, 도서 규모</p>
      </div>
    </main>
  );
}

export default Info;
