<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DigiBenis | دیده شو!</title>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg:#07080C; --card:#12151E; --tx:#ECEDF2; --soft:#9EA3B5; --ln:rgba(255,255,255,.09); --gold:#C9A24B; }
        @media(prefers-color-scheme:light){:root:not([data-theme="dark"]){ --bg:#F6F4EE; --card:#fff; --tx:#14161F; --soft:#585D70; --ln:rgba(10,14,26,.12); --gold:#8A6A1F; }}
        
        *{box-sizing:border-box;margin:0;padding:0} 
        html{scroll-behavior:smooth;} /* فعال سازی اسکرول نرم */
        body{font-family:'Vazirmatn',sans-serif;background:var(--bg);color:var(--tx);line-height:1.9;overflow-x:hidden}
        a{color:inherit;text-decoration:none}.w{max-width:1120px;margin:0 auto;padding:0 20px}
        
        /* هدر و منو */
        header{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 85%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--ln);height:70px;display:flex;align-items:center;justify-content:space-between;padding:0 5%}
        .logo{font-weight:800;font-size:20px}.logo b{color:var(--gold)}
        .nav-links a{margin-right:20px;font-size:14px;color:var(--soft);transition:.2s}
        .nav-links a:hover{color:var(--gold)}
        .btn-blog{padding:8px 16px;border-radius:20px;border:1px solid var(--gold);color:var(--gold);font-size:13px;font-weight:700;transition:.2s}
        .btn-blog:hover{background:var(--gold);color:#000}

        section{padding:80px 0}.k{color:var(--gold);font-size:13px;letter-spacing:.04em;display:block;margin-bottom:10px}
        h1{font-size:clamp(2rem,5vw,3rem);line-height:1.4;margin-bottom:12px}.sub{color:var(--soft);max-width:660px;margin-bottom:36px}
        
        /* گرید مقالات */
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
        .c{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:24px;transition:.3s;cursor:pointer}
        .c:hover{border-color:var(--gold);transform:translateY(-4px)}
        .ph{aspect-ratio:16/9;border-radius:10px;margin-bottom:16px;background:var(--bg);background-size:cover;background-position:center}
        .c h3{font-size:18px;margin-bottom:8px}.c p{color:var(--soft);font-size:15px;line-height:1.8}
        .read-more{color:var(--gold);font-size:13px;font-weight:700;margin-top:16px;display:block}
        
        /* استایل مودال (پنجره بازشونده) */
        #article-modal{display:none;position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,0.85);backdrop-filter:blur(8px);overflow-y:auto;padding:40px 20px}
        .modal-inner{max-width:800px;margin:40px auto;background:var(--card);border-radius:20px;padding:40px;position:relative;border:1px solid var(--ln);animation:fadeIn .3s ease}
        @keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        .close-btn{position:absolute;top:20px;left:20px;background:none;border:none;color:var(--soft);font-size:28px;cursor:pointer;transition:.2s;line-height:1}
        .close-btn:hover{color:var(--tx);transform:rotate(90deg)}
        .category-tag{display:inline-block;padding:4px 12px;border-radius:20px;background:var(--bg);border:1px solid var(--ln);color:var(--gold);font-size:13px;font-weight:700;margin-bottom:15px}
        .meta-info{color:var(--soft);font-size:14px;display:flex;gap:15px;margin-bottom:30px;flex-wrap:wrap}
        .content p{margin-bottom:24px;font-size:18px;line-height:2.1} 
        .content h2{font-size:1.6rem;margin:40px 0 20px;color:var(--gold);border-right:4px solid var(--gold);padding-right:15px}
        blockquote{background:var(--bg);border-right:4px solid var(--gold);padding:20px 25px;margin:30px 0;border-radius:8px;font-style:italic;color:var(--soft)}
        footer{text-align:center;padding:40px 0;color:var(--soft);font-size:13px;border-top:1px solid var(--ln);margin-top:60px}
    </style>
</head>
<body>
    <header>
        <a href="#" class="logo">Digi<b>Benis</b></a>
        <div class="nav-links">
            <!-- لینک مخصوص مشاهده وبلاگ -->
            <a href="#blog" class="btn-blog">مشاهده مقالات وبلاگ DigiBenis</a>
        </div>
    </header>

    <main>
        <!-- بخش وبلاگ با آیدی blog برای لینک دهی -->
        <section id="blog" class="w">
            <span class="k">وبلاگ DigiBenis</span>
            <h1>جدیدترین نوشته‌ها</h1>
            <p class="sub">برای خواندن هر مقاله، روی کارت آن کلیک کنید.</p>
            <div id="blog-container" class="grid"></div>
        </section>
    </main>

    <!-- پنجره بازشونده مقاله -->
    <div id="article-modal">
        <div class="modal-inner">
            <button class="close-btn" onclick="closeArticle()">✕</button>
            <div id="modal-content"></div>
        </div>
    </div>

    <footer><p>© ۱۴۰۳ DigiBenis. تمامی حقوق محفوظ است.</p></footer>

    <!-- لود کردن داده‌ها و اسکریپت نمایش -->
    <script src="articles.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const container = document.getElementById('blog-container');
            if (container && typeof articlesData !== 'undefined') {
                container.innerHTML = articlesData.map(article => `
                    <div class="c" onclick="openArticle('${article.id}')">
                        <div class="ph" style="background-image: url('${article.image}')"></div>
                        <span class="k">${article.category}</span>
                        <h3>${article.title}</h3>
                        <p>${article.excerpt}</p>
                        <span class="read-more">ادامه مطلب ←</span>
                    </div>
                `).join('');
            }
        });

        function openArticle(id) {
            const article = articlesData.find(a => a.id === id);
            if (!article) return;
            
            document.getElementById('modal-content').innerHTML = `
                <span class="category-tag">${article.category}</span>
                <h1>${article.title}</h1>
                <div class="meta-info">
                    <span>📅 ${article.date}</span>
                    <span>⏱️ ${article.readTime}</span>
                    <span>✍️ احمد صفاربنیس</span>
                </div>
                <div class="ph" style="width:100%; aspect-ratio:16/9; background-image:url('${article.image}'); margin-bottom:30px;"></div>
                <article class="content">${article.content}</article>
            `;
            
            const modal = document.getElementById('article-modal');
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // قفل کردن اسکرول صفحه اصلی
        }

        function closeArticle() {
            document.getElementById('article-modal').style.display = 'none';
            document.body.style.overflow = 'auto'; // آزاد کردن اسکرول
        }

        // بستن مودال با کلیک روی فضای خالی اطراف
        document.getElementById('article-modal').addEventListener('click', function(e) {
            if (e.target === this) closeArticle();
        });
        
        // بستن مودال با دکمه Escape کیبورد
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeArticle();
        });
    </script>
</body>
</html>
