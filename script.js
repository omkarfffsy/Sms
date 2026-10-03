document.addEventListener('DOMContentLoaded', () => {

const appWrapper = document.getElementById('app-wrapper');
const glassNav = document.querySelector('.glass-nav');

// =====================================================================
// HOW TO ADD VIDEOS TO THE MAIN HOME SCREEN (Slider & Carousels)
// =====================================================================
const seriesData = [
    { id: 1, title: "MATHS 2 CH 1 LECTURE 1 DIFFERENTIATION", category: "12 TOPPERS BATCH MATHS 2026", isFeatured: true, image: "https://thumbs2.imgbox.com/60/35/PDj2Crbv_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/60/35/PDj2Crbv_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADiA0AAsVQ4EQDApqajl1oYhYE" }] },
    { id: 2, title: "MATHS 2 CH 1 LECTURE 2 DIFFERENTIATION", category: "12 TOPPERS BATCH MATHS 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/fe/23/mRT7ZfTH_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/fe/23/mRT7ZfTH_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADEw4AAsVQ4EQpEWXjA5tZkxYE" }] },
    { id: 3, title: "MATHS 2 CH 1 LECTURE 3 DIFFERENTIATION", category: "12 TOPPERS BATCH MATHS 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/13/04/FtdPfkdh_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/13/04/FtdPfkdh_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADnAkAAk4QAUWIVTnI0b5n0xYE" }] },
    { id: 4, title: "MATHS 2 CH 1 LECTURE 4 DIFFERENTIATION", category: "12 TOPPERS BATCH MATHS 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/f1/4e/PUEFu2tV_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/f1/4e/PUEFu2tV_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADDgoAAk4QAUVaIPl9NtivhBYE" }] },
    { id: 500, title: "CH 10 LECTURE 1 HALOGEN DERIVATION", category: "12 CRASH COURSE CHEMISTRY 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/94/bf/pXys7Xwr_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/94/bf/pXys7Xwr_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADAxMAAk4QCUVB_QZvMrp6gxYE" }] },
  
    { id: 600, title: "MATHS 2 CH 1 LELECTUR 1 DIFFERENTIATION", category: "12 CRASH COURSE MATHS 2 2026", isFeatured: true, image: "https://thumbs2.imgbox.com/aa/f5/lHobrX4W_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/aa/f5/lHobrX4W_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADqRIAAk4QCUUIkLo2G9dhZBYE" }] },
    { id: 601, title: "MATHS 2 CH 1 LELECTUR 2 DIFFERENTIATION", category: "12 CRASH COURSE MATHS 2 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/a0/66/a9VR64se_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/a0/66/a9VR64se_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADPBMAAl_CEUV8HcnHY9MCvRYE" }] },
    
    { id: 602, title: "MATHS 2 CH 1 LELELECTUR 3 DIFFERENTIATION", category: "12 CRASH COURSE MATHS 2 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/c9/3e/WBuKhhhh_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/c9/3e/WBuKhhhh_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQAD9gsAAtq5IEUxeFC-nwrpoRYE" }] },
    
    { id: 603, title: "MATHS 2 CH 1 LELELECTUR 4 DIFFERENTIATION", category: "12 CRASH COURSE MATHS 2 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/a9/1b/DENt4bSi_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/a9/1b/DENt4bSi_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQAD9A8AAtq5MEV-ZmdrQNrJiBYE" }] },
    
     { id: 604, title: "MATHS 2 CH 1 LELELECTUR 5 DIFFERENTIATION", category: "12 CRASH COURSE MATHS 2 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/17/70/TpXpEDKK_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/17/70/TpXpEDKK_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQAD-wkAAhuCOUUJ3_oQ3wOrxBYE" }] },
     
     { id: 700, title: "MATHS 1 CH 1 LELELECTUR 1 LOGIC", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/bf/15/G7obXCaN_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/bf/15/G7obXCaN_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADtA4AAhuCOUWe8WXPfelPZBYE" }] },
     { id: 701, title: "MATHS 1 CH 1 LELELECTUR 2 LOGIC", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/14/ff/l7oBwvG4_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/14/ff/l7oBwvG4_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADXg4AAhuCOUX0CXgsybIFwhYE" }] },
{ id: 702, title: "MATHS 1 CH 1 LELELECTUR 3 LOGIC", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/f3/d6/r7OsyG2j_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/f3/d6/r7OsyG2j_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADCwYAAooGUUWe5rZPZoDOlRYE" }] },

{ id: 703, title: "MATHS 1 CH 2 LELELECTUR 1 Matrices", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/30/86/dpCnSN6d_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/30/86/dpCnSN6d_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADWhAAAlTOaEUGkGl4CPHidhYE" }] },
     
     { id: 704, title: "MATHS 1 CH 2 LELELECTUR 2 Matrices", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/ab/da/uISw0xbX_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/ab/da/uISw0xbX_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADKxUAAi5wOEQ-6w_I71UAAZ0WBA" }] },


{ id: 707, title: "MATHS 1 CH 3 LELELECTUR 1 Trigonometric Functions ", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/e2/be/mQc746dF_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/e2/be/mQc746dF_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADNwoAAhbgQUT-F0XjUm53GBYE" }] },


{ id: 708, title: "MATHS 1 CH 3 LELELECTUR 2 Trigonometric Functions ", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/f9/aa/MiBs1G2v_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/f9/aa/MiBs1G2v_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADSgoAAhbgQUTKrhSk5_4CERYE" }] },


{ id: 709, title: "MATHS 1 CH 3 LELELECTUR 3 Trigonometric Functions ", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/2e/1d/Cr5SU92G_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/2e/1d/Cr5SU92G_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADbAoAAhbgQURzsePgae8F6hYE" }] },








 { id: 705, title: "MATHS 1 CH 4 LELELECTUR 1 Pair of straight line ", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/98/b7/S1IjsmMc_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/98/b7/S1IjsmMc_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADVgkAAhbgQURblyqKF8RI9RYE" }] },

{ id: 706, title: "MATHS 1 CH 4 LELELECTUR 2 Pair of straight line ", category: "12 CRASH COURSE MATHS 1 2026", isFeatured: false, image: "https://thumbs2.imgbox.com/4c/e7/BOLDzTA5_t.jpg", episodes: [{ thumbnail: "https://thumbs2.imgbox.com/4c/e7/BOLDzTA5_t.jpg", mainLink: "https://t.me/File_store_1a21_bot?start=BQADAQADFQoAAhbgQURpr6PM4t8OuxYE" }] },


     
    
    { id: 301, title: " Solid State", category: "Chemistry", isFeatured: true, image: "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=800&auto=format&fit=crop&q=60", episodes: [{ thumbnail: "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=800&auto=format&fit=crop&q=60", mainLink: "#" }] },
    { id: 302, title: "Chemistry Chapter 2: Solutions", category: "Chemistry", isFeatured: false, image: "https://images.unsplash.com/photo-1603126852818-189f33c09b82?w=800&auto=format&fit=crop&q=60", episodes: [{ thumbnail: "https://images.unsplash.com/photo-1603126852818-189f33c09b82?w=800&auto=format&fit=crop&q=60", mainLink: "#" }] },
    { id: 303, title: "Chemistry Chapter 3: Ionic Equilibria", category: "Chemistry", isFeatured: false, image: "https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&auto=format&fit=crop&q=60", episodes: [{ thumbnail: "https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&auto=format&fit=crop&q=60", mainLink: "#" }] }
];  

// =====================================================================
// HOW TO ADD FOLDERS AND LINKS TO "PLAYLISTS" & "NOTES"
// =====================================================================
const courseData = {
 
  "TOPPERS BATCH 2026": {
    "Maths 2 (Std 12)": [
        { 
            chapterName: "1. DIFFERENTIATION", 
            videos: [ 
                {title: "Lecture 1", url: "https://t.me/File_store_1a21_bot?start=BQADAQADiA0AAsVQ4EQDApqajl1oYhYE"}, 
                {title: "Lecture 2", url: "https://t.me/File_store_1a21_bot?start=BQADAQADEw4AAsVQ4EQpEWXjA5tZkxYE"} ,
                {title: "LECTURE 3", url: "https://t.me/File_store_1a21_bot?start=BQADAQADnAkAAk4QAUWIVTnI0b5n0xYE"} ,
                {title: "LECTURE 4", url: "https://t.me/File_store_1a21_bot?start=BQADAQADDgoAAk4QAUVaIPl9NtivhBYE" }
            ], 
            notes: [ 
                {title: "omkar soni", url: "#"} 
            ] 
        },
        { 
            chapterName: "2. Functions", 
            videos: [ 
                {title: "Lecture 1: Intro", url: "#"} 
            ], 
            notes: [ 
                {title: "Function Graphs PDF", url: "#"} 
            ] 
        }
    ]
  }, 

  "CRASH COURSE 2026": {
    "Chemistry (Std 12)": [
        { 
            chapterName: "10. Halogen Derivatives", 
            videos: [ 
                {title: "Lecture 1: Halogen Derivation", url: "https://t.me/File_store_1a21_bot?start=BQADAQADAxMAAk4QCUVB_QZvMrp6gxYE"} 
            ], 
            notes: [ 
                {title: "coming ", url: "  "} 
            ] 
        }
    ], // <--- Comma separating Chemistry and Maths inside Crash Course
    "Maths 2 (Std 12)": [
        { 
            chapterName: "1. DIFFERENTIATION", 
            videos: [ 
                {title: "Lecture 1: Intro", url: "https://t.me/File_store_1a21_bot?start=BQADAQADqRIAAk4QCUUIkLo2G9dhZBYE"} ,
                {title: "LECTURE 2" ,
                url:"https://t.me/File_store_1a21_bot?start=BQADAQADPBMAAl_CEUV8HcnHY9MCvRYE"} ,
                {title: "LECTURE 3" ,
                url: "https://t.me/File_store_1a21_bot?start=BQADAQAD9gsAAtq5IEUxeFC-nwrpoRYE" } ,
                {title: "LECTURE 4" ,
                url: "https://t.me/File_store_1a21_bot?start=BQADAQAD9A8AAtq5MEV-ZmdrQNrJiBYE"},
                {title:"LECTURE 5" ,
                url: "https://t.me/File_store_1a21_bot?start=BQADAQAD-wkAAhuCOUUJ3_oQ3wOrxBYE" }
            ], 
            notes: [ 
                {title: "MATHS 2 CH 1 BRAHMASTRA LITE", url: "https://t.me/File_store_1a21_bot?start=BQADAQAD3xIAAl_CEUXsy2JMylb96xYE"} ,
                {title: "TARGET MATHS 2 CH 1 MQC" , url: "https://t.me/File_store_1a21_bot?start=BQADAQADkgsAAtq5IEU65ES64i4cghYE" }
            ] 
        }
    ] ,
    "Maths 1 (Std 12)": [
          { chapterName: "LOGIC ", 
          videos: [ 
            {title: "Lecture 1: ", url: "https://t.me/File_store_1a21_bot?start=BQADAQADtA4AAhuCOUWe8WXPfelPZBYE"}, 
            {title: "LECTURE 2" ,
            url: "https://t.me/File_store_1a21_bot?start=BQADAQADXg4AAhuCOUX0CXgsybIFwhYE" },
            {title:"Lecture 3" ,
            url:"https://t.me/File_store_1a21_bot?start=BQADAQADCwYAAooGUUWe5rZPZoDOlRYE" },
          
          
          
          
          
      ] ,
      notes: [ 
                {title: "MATHS 1 CH 1 BRAHMASTRA LITE", 
                url: "#"} ,
                ]
    
  } 
  ] 
  },
  
  "Maths": {
      "Std 11": [
          { chapterName: "1. Sets and Relations", videos: [ {title: "Lecture 1: Intro to Sets", url: "#"}, {title: "Lecture 2: Subsets", url: "#"} ], notes: [ {title: "Full Chapter Notes", url: "#"} ] },
          { chapterName: "2. Functions", videos: [ {title: "Lecture 1: Intro", url: "#"} ], notes: [ {title: "Function Graphs PDF", url: "#"} ] }
      ],
      "Std 12": [
          { chapterName: "1. Mathematical Logic", videos: [ {title: "Lecture 1: Statements", url: "#"} ], notes: [ {title: "Logic Truth Tables", url: "#"} ] },
          { chapterName: "2. Matrices", videos: [ {title: "Lecture 1: Adjoint", url: "#"} ], notes: [ {title: "Matrices Notes", url: "#"} ] },
          { chapterName: "3. Integration", videos: [ {title: "Lecture 1: Basics", url: "#"} ], notes: [ {title: "Integration Shortcuts", url: "#"} ] }
      ]
  },
  "Physics": {
      "Std 11": [
          { chapterName: "1. Units and Measurements", videos: [ {title: "Lec 1: Intro", url: "#"} ], notes: [ {title: "Notes", url: "#"} ] },
          { chapterName: "2. Mathematical Methods", videos: [ {title: "Lec 1: Vectors", url: "#"} ], notes: [ {title: "Notes", url: "#"} ] }
      ],
      "Std 12": [
          { chapterName: "1. Rotational Dynamics", videos: [ {title: "Lec 1: Circular Motion", url: "#"} ], notes: [ {title: "Full Chapter Notes", url: "#"} ] },
          { chapterName: "2. Mechanical Properties of Fluids", videos: [ {title: "Lec 1: Pressure", url: "#"} ], notes: [ {title: "Full Chapter Notes", url: "#"} ] }
      ]
  },
  "Chemistry": {
      "Std 11": [
          { chapterName: "1. Some Basic Concepts of Chemistry", videos: [ {title: "Lec 1: Matter", url: "#"} ], notes: [ {title: "Mole Concept Tricks", url: "#"} ] },
          { chapterName: "4. Structure of Atom", videos: [ {title: "Lec 1: Discovery", url: "#"} ], notes: [ {title: "Structure of Atom PDF", url: "#"} ] },
          { chapterName: "5. Chemical Bonding", videos: [ {title: "Lec 1: Ionic Bond", url: "#"} ], notes: [ {title: "Hybridization Chart", url: "#"} ] }
      ],
      "Std 12": [
          { chapterName: "1. Solid State", videos: [ {title: "Lec 1: Types of Solids", url: "#"} ], notes: [ {title: "Solid State Short Notes", url: "#"} ] },
          { chapterName: "2. Solutions", videos: [ {title: "Lec 1: Concentration", url: "#"} ], notes: [ {title: "Solutions Formula Sheet", url: "#"} ] },
          { chapterName: "3. Ionic Equilibria", videos: [ {title: "Lec 1: Acids & Bases", url: "#"} ], notes: [ {title: "Ionic Equilibria PDF", url: "#"} ] },
          { chapterName: "4. Chemical Thermodynamics", videos: [ {title: "Lec 1: Introduction", url: "#"} ], notes: [ {title: "Thermodynamics Notes", url: "#"} ] }
      ]
  }
};

// --- UI Elements Reference ---
const ui = {  
    preloader: document.getElementById('preloader'), mainContent: document.getElementById('app-main-content'),  
    nav: { container: document.querySelector('.glass-nav'), items: document.querySelectorAll('.nav-item'), spotlight: document.querySelector('.nav-spotlight') },  
    contentSections: document.getElementById('content-sections'),  
    hero: { slider: document.getElementById('hero-slider'), dots: document.getElementById('hero-dots'), prevBtn: document.getElementById('hero-prev'), nextBtn: document.getElementById('hero-next') },  
    watchView: document.getElementById('watch-view'), categoryView: document.getElementById('category-view'),  
    dirView: document.getElementById('directory-view'),
    search: { input: document.getElementById('search-page-input'), suggestionsContainer: document.getElementById('search-suggestions') }
};  

const state = { activeSeries: null, likedItems: new Set(), featuredItems: seriesData.filter(s => s.isFeatured), slideInterval: null, currentSlide: 0 };  

// --- SEARCH ENGINE INITIALIZATION ---
const allSearchableData = [...seriesData]; 
Object.keys(courseData).forEach(subject => {
    Object.keys(courseData[subject]).forEach(std => {
        courseData[subject][std].forEach(chap => {
            allSearchableData.push({
                isFolderItem: true,
                title: `${chap.chapterName} (${subject} ${std})`,
                image: `https://placehold.co/80x50/161b22/00ddb5?text=${subject.substring(0,3)}`,
                subject: subject,
                std: std,
                chapter: chap.chapterName
            });
        });
    });
});
let fuse;

// --- DIRECTORY NAVIGATION LOGIC (Folders) ---
let dirState = { mode: null, subject: null, std: null, chapter: null };

// Opens the root directory (Subject level)
const openDirectory = (mode) => {
    dirState = { mode: mode, subject: null, std: null, chapter: null };
    renderDirectoryUI();
    document.querySelectorAll('.app-view').forEach(v => v.classList.add('hidden'));
    ui.dirView.classList.remove('hidden');
    ui.mainContent.scrollTop = 0;
};

// Handles clicking into a folder
document.getElementById('dir-container').addEventListener('click', (e) => {
    const card = e.target.closest('.folder-card');
    if (!card) return;
    dirState[card.dataset.level] = card.dataset.value;
    renderDirectoryUI();
});

// Handles the back button inside folders
document.getElementById('dir-back-btn').addEventListener('click', () => {
    if (dirState.chapter) { dirState.chapter = null; }
    else if (dirState.std) { dirState.std = null; }
    else if (dirState.subject) { dirState.subject = null; }
    else { return navigateTo('home-view'); } 
    renderDirectoryUI();
});

// Draws the folders or files on the screen based on where you are
const renderDirectoryUI = () => {
    const container = document.getElementById('dir-container');
    const headerTitle = document.getElementById('dir-title');
    const isNotes = dirState.mode === 'notes';
    const themeColor = isNotes ? '#2AABEE' : '#00ddb5'; 
    const rootTitle = isNotes ? 'Notes & PDFs' : 'Chapter Playlists';

    if (!dirState.subject) {
        headerTitle.textContent = rootTitle;
        container.innerHTML = Object.keys(courseData).map(sub => `
            <div class="folder-card" data-level="subject" data-value="${sub}">
                <i class="fas fa-folder" style="color:${themeColor}"></i>
                <span>${sub}</span>
            </div>
        `).join('');
    } else if (dirState.subject && !dirState.std) {
        headerTitle.textContent = dirState.subject;
        container.innerHTML = Object.keys(courseData[dirState.subject] || {}).map(std => `
            <div class="folder-card" data-level="std" data-value="${std}">
                <i class="fas fa-layer-group" style="color:${themeColor}"></i>
                <span>${std}</span>
            </div>
        `).join('');
    } else if (dirState.subject && dirState.std && !dirState.chapter) {
        headerTitle.textContent = `${dirState.subject} - ${dirState.std}`;
        const chapters = courseData[dirState.subject]?.[dirState.std] || [];
        container.innerHTML = chapters.map(chap => `
            <div class="folder-card" data-level="chapter" data-value="${chap.chapterName}">
                <i class="fas fa-folder-open" style="color:${themeColor}"></i>
                <span>${chap.chapterName}</span>
            </div>
        `).join('');
    } else {
        headerTitle.textContent = dirState.chapter;
        const chapters = courseData[dirState.subject]?.[dirState.std] || [];
        const selectedChapter = chapters.find(c => c.chapterName === dirState.chapter);
        const files = isNotes ? (selectedChapter?.notes || []) : (selectedChapter?.videos || []);
        
        if (files.length > 0) {
            container.innerHTML = files.map(file => `
                <a href="${file.url}" target="_blank" class="file-card">
                    <i class="fas ${isNotes ? 'fa-file-pdf' : 'fa-play-circle'}" style="color:${isNotes ? '#ff4d4d' : themeColor}"></i>
                    <div class="file-info">
                        <h4>${file.title}</h4>
                        <span>${isNotes ? 'Click to open PDF' : 'Click to watch Video'}</span>
                    </div>
                    <i class="fas fa-chevron-right action-icon"></i>
                </a>
            `).join('');
        } else {
            container.innerHTML = `<p style="text-align: center; color: var(--text-secondary); margin-top: 2rem;">No items uploaded for this chapter yet.</p>`;
        }
    }
};

// --- APP BOTTOM NAVIGATION ---
const renderView = (viewId) => {  
    if (viewId === 'directory-view') return; 
    const parts = viewId.split('/');
    const baseView = parts[0];
    const p1 = parts[1] ? decodeURIComponent(parts[1]) : null;
    
    document.querySelectorAll('.app-view').forEach(v => v.classList.toggle('hidden', v.id !== baseView));  
    
    if (baseView === 'watch-view') {  
        const series = seriesData.find(s => s.id === parseInt(p1, 10));  
        if (series) renderWatchPage(series);  
    } else if (baseView === 'likes-view') {  
        renderLikesPage();  
    } else if (baseView === 'category-view') {  
        renderCategoryPage(p1);  
    }
    
    const activeItem = document.querySelector(`.nav-item[data-view="${baseView}"]`);  
    ui.nav.items.forEach(item => item.classList.remove('active'));  
    if (activeItem) {  
        activeItem.classList.add('active');  
        const newLeft = activeItem.offsetLeft + (activeItem.offsetWidth / 2) - (ui.nav.spotlight.offsetWidth / 2);  
        ui.nav.spotlight.style.transform = `translateX(${newLeft}px)`;  
    }  
    ui.mainContent.scrollTop = 0;  
};  
  
const navigateTo = (viewId) => { history.pushState({ viewId }, '', `#${viewId}`); renderView(viewId); };  
window.addEventListener('popstate', (event) => { renderView(event.state?.viewId || 'home-view'); });  

const createCardElement = (series) => `<div class="series-card-item" data-id="${series.id}"><div class="series-card-image-container"><img src="${series.image}"></div><h3 class="series-card-title-outer">${series.title}</h3></div>`;  

// Renders the Home Screen (Slider + Categories)
const renderHomePage = () => {  
    ui.hero.slider.innerHTML = state.featuredItems.map((s, i) => `<div class="hero-slide" data-id="${s.id}"><img src="${s.image}"><h2 class="hero-title">${s.title}</h2><button class="pro-button small watch-now-btn" data-id="${s.id}"><i class="fas fa-play"></i> Start Learning</button></div>`).join('');  
    ui.hero.dots.innerHTML = state.featuredItems.map((_, i) => `<div class="hero-dot ${i === 0 ? 'active' : ''}" data-slide="${i}"></div>`).join('');  
      
    const categories = [...new Set(seriesData.map(s => s.category))];  
    ui.contentSections.innerHTML = categories.map(cat => {  
        const items = seriesData.filter(i => i.category === cat).slice(0, 10);  
        return items.length ? `<section class="content-section"><div class="section-header"><h2 class="section-title">${cat}</h2><a href="#" class="view-more-btn" data-category="${cat}">View All <i class="fas fa-arrow-right"></i></a></div><div class="series-carousel">${items.map(createCardElement).join('')}</div></section>` : '';  
    }).join('');  
};  

const renderWatchPage = (series) => {  
    state.activeSeries = series;  
    const isLiked = state.likedItems.has(series.id);  
    ui.watchView.innerHTML = `<div class="watch-view-content"><button class="pro-button small secondary back-btn"><i class="fas fa-arrow-left"></i></button><div class="featured-image-container"><img id="featured-image" src="${series.episodes[0].thumbnail}"><div style="position: absolute; inset: 0; background: linear-gradient(to top, var(--dark-bg) 5%, transparent 40%);"></div></div><div class="watch-view-header"><h2 id="featured-title">${series.title}</h2><button id="like-btn" class="like-button ${isLiked ? 'liked' : ''}"><i class="${isLiked ? 'fas' : 'far'} fa-bookmark"></i></button></div><div class="watch-buttons"><a href="${series.episodes[0].mainLink}" target="_blank" class="pro-button primary">Watch Lecture <i class="fas fa-play-circle"></i></a></div></div>`;  
};  

const renderLikesPage = () => {  
    const likedSeries = seriesData.filter(s => state.likedItems.has(s.id));  
    document.getElementById('likes-grid').innerHTML = likedSeries.length ? likedSeries.map(createCardElement).join('') : '';  
};  

const renderCategoryPage = (category) => {  
    const items = seriesData.filter(s => s.category === category);  
    ui.categoryView.innerHTML = `<header class="view-header"><button class="pro-button small secondary back-btn-header"><i class="fas fa-arrow-left"></i></button><h1 class="view-title">${category}</h1></header><div class="results-grid">${items.map(createCardElement).join('')}</div>`;  
};  

const handleSearch = (query) => {  
    if (query.length < 1) { ui.search.suggestionsContainer.innerHTML = ''; return; }  
    const results = fuse.search(query).slice(0, 8).map(r => r.item);  
    ui.search.suggestionsContainer.innerHTML = results.map(s => {
        if(s.isFolderItem) {
            return `<div class="suggestion-item" data-type="folder" data-sub="${s.subject}" data-std="${s.std}" data-chap="${s.chapter}">
                        <img src="${s.image}"><span>${s.title}</span>
                    </div>`;
        } else {
            return `<div class="suggestion-item" data-id="${s.id}">
                        <img src="${s.image}"><span>${s.title}</span>
                    </div>`;
        }
    }).join('');  
};  
  
// --- HERO SLIDER ANIMATION ---
let isSliderAnimating = false;
const handleHeroNav = (direction) => { 
    if (isSliderAnimating) return;
    isSliderAnimating = true;
    const count = state.featuredItems.length; 
    state.currentSlide = (state.currentSlide + direction + count) % count; 
    ui.hero.slider.style.transition = 'transform 0.5s ease'; ui.hero.slider.style.transform = `translateX(-${state.currentSlide * 100}%)`; ui.hero.dots.querySelectorAll('.hero-dot').forEach((d, i) => d.classList.toggle('active', i === state.currentSlide));
    clearInterval(state.slideInterval); state.slideInterval = setInterval(() => handleHeroNav(1), 3000);
    setTimeout(() => isSliderAnimating = false, 500);
};  
  
const handleGlobalClick = (e) => {  
    const card = e.target.closest('.series-card-item, .hero-slide, .watch-now-btn');  
    const viewMore = e.target.closest('.view-more-btn');  
    const suggestion = e.target.closest('.suggestion-item');

    if (suggestion) {
        if (suggestion.dataset.type === 'folder') {
            dirState = { mode: 'playlist', subject: suggestion.dataset.sub, std: suggestion.dataset.std, chapter: suggestion.dataset.chap };
            document.querySelectorAll('.app-view').forEach(v => v.classList.add('hidden'));
            ui.dirView.classList.remove('hidden');
            renderDirectoryUI();
            ui.search.input.value = '';
            ui.search.suggestionsContainer.innerHTML = '';
            return;
        } else if (suggestion.dataset.id) {
            return navigateTo(`watch-view/${suggestion.dataset.id}`);
        }
    }

    if (card?.dataset.id) return navigateTo(`watch-view/${card.dataset.id}`);  
    if (viewMore?.dataset.category) { e.preventDefault(); return navigateTo(`category-view/${encodeURIComponent(viewMore.dataset.category)}`); }  
    if (e.target.closest('.back-btn, .back-btn-header') && !e.target.closest('#dir-back-btn')) return history.back();  
    
    // Bookmark Button Logic
    if (e.target.closest('#like-btn')) {
        const id = state.activeSeries.id;
        state.likedItems.has(id) ? state.likedItems.delete(id) : state.likedItems.add(id);  
        localStorage.setItem('likedSeries', JSON.stringify([...state.likedItems]));  
        e.target.closest('#like-btn').classList.toggle('liked', state.likedItems.has(id));
        e.target.closest('#like-btn').querySelector('i').className = state.likedItems.has(id) ? 'fas fa-bookmark' : 'far fa-bookmark';
        document.getElementById('stat-total-likes').textContent = state.likedItems.size;
    }
};  

// --- BOOT UP THE APP ---
function initializeMainApp() {
    appWrapper.classList.remove('hidden');
    glassNav.classList.remove('hidden');
    
    setTimeout(() => { ui.preloader.classList.add('fade-out'); }, 800);
    
    // Turn on the search engine
    fuse = new Fuse(allSearchableData, { keys: ['title', 'chapter', 'subject'], threshold: 0.4 });
    
    renderHomePage();  
    state.likedItems = new Set(JSON.parse(localStorage.getItem('likedSeries') || '[]').map(Number));  
    document.getElementById('stat-total-likes').textContent = state.likedItems.size;

    const initialView = window.location.hash.slice(1) || 'home-view';  
    history.replaceState({ viewId: 'home-view' }, '', `#home-view`);  
    if (initialView !== 'home-view') history.pushState({ viewId: initialView }, '', `#${initialView}`); 
    renderView(initialView);  
    
    // Auto-slide the top banner
    state.slideInterval = setInterval(() => handleHeroNav(1), 3000);  
      
    // Set up button clicks
    ui.nav.container.addEventListener('click', e => { const navLink = e.target.closest('.nav-item'); if (navLink) { e.preventDefault(); navigateTo(navLink.dataset.view); }});  
    document.body.addEventListener('click', handleGlobalClick);  
    ui.hero.prevBtn.addEventListener('click', () => handleHeroNav(-1));  
    ui.hero.nextBtn.addEventListener('click', () => handleHeroNav(1));  
    ui.search.input.addEventListener('input', (e) => handleSearch(e.target.value));

    // Connect the Manual Buttons (Playlist and Notes)
    document.getElementById('btn-playlist').addEventListener('click', () => openDirectory('playlist'));
    document.getElementById('btn-notes').addEventListener('click', () => openDirectory('notes'));
}

// --- DISCLAIMER MODAL LOGIC ---
const modalOverlay = document.getElementById('modal-overlay');
const ageGateYesBtn = document.getElementById('age-gate-yes');
const ageGateNoBtn = document.getElementById('age-gate-no');

if (sessionStorage.getItem('isAgeVerified') === 'true') {  
    initializeMainApp();  
} else {  
    modalOverlay.classList.remove('hidden');  
    ageGateYesBtn.addEventListener('click', () => {  
        sessionStorage.setItem('isAgeVerified', 'true');  
        modalOverlay.classList.add('hidden');  
        initializeMainApp();  
    });  
    ageGateNoBtn.addEventListener('click', () => { 
        document.body.innerHTML = `<div style="display:flex; flex-direction: column; justify-content:center;align-items:center;height:100vh;background-color:#101418;color:#f0f0f5;font-family:'Poppins',sans-serif; text-align: center; padding: 1rem;"><h1>Take Your Time!</h1><p>Refresh the page when you are ready to start studying.</p></div>`; 
    });  
}

});
