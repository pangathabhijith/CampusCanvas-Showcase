import { useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { Link, Route, Router as WouterRouter, Switch, useLocation, useParams } from 'wouter';
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, Bookmark, Check, ChevronDown,
  CircleHelp, Compass, Eye, Flag, Heart, ImagePlus, LogIn, LogOut, MessageCircle,
  Palette, Search, Send, ShieldCheck, Sparkles, Star, TrendingUp,
  UserRound, Users, X, PenLine, CalendarDays, MapPin, Plus, Clock3, Camera,
} from 'lucide-react';
import {
  useGetSession, useLogin, useLogout, useRegister, useGetPosts, useGetPost, useCreatePost,
  useToggleLike, useToggleBookmark, useAddComment, useReportPost, useGetMyProfile,
  useUpdateMyProfile, useGetUserProfile, useToggleFollow, useGetCreators, useGetEvents,
  useEnterEvent, useCreateEvent, useGetAdminSummary, useGetAdminPosts, useModeratePost,
  useGetAdminReports, useResolveReport, useGetAdminUsers, useSetUserStatus,
  useUploadAvatar, useSharePost, useGetBookmarks, getGetBookmarksQueryKey,
  getGetSessionQueryKey, getGetPostsQueryKey, getGetPostQueryKey, getGetEventsQueryKey,
  getGetMyProfileQueryKey, getGetUserProfileQueryKey, getGetCreatorsQueryKey,
  getGetAdminSummaryQueryKey, getGetAdminPostsQueryKey, getGetAdminReportsQueryKey,
  getGetAdminUsersQueryKey, setCsrfTokenGetter,
} from '@workspace/api-client-react';
import type { Event, Post, User } from '@workspace/api-client-react';

const queryClient = new QueryClient();
let csrfToken = '';
setCsrfTokenGetter(() => csrfToken || null);
const categories = [
  'All work',
  'Drawing & Painting',
  'Photography',
  'Writing',
  'Poetry',
  'Music & Audio',
  'Film & Video',
  'Graphic Design',
  'College Life & Events',
];
const navItems = [
  { href: '/', label: 'Home', icon: Compass },
  { href: '/explore', label: 'Explore', icon: Search },
  { href: '/trending', label: 'Trending', icon: TrendingUp },
  { href: '/events', label: 'Campus events', icon: CalendarDays },
];
const mutRequest = () => ({});

function initials(name = '') {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0] ?? '').join('').toUpperCase() || 'CC';
}
function Avatar({ src, name, size = 'md' }: { src?: string | null; name?: string; size?: 'sm' | 'md' | 'lg' }) {
  return <span className={`avatar avatar-${size}`} aria-label={name || 'Creator'}>{src ? <img src={src} alt="" /> : initials(name)}</span>;
}
function ErrorNotice({ retry, text = 'We couldn’t load this just now.' }: { retry?: () => void; text?: string }) {
  return <div className="state-panel"><span className="state-mark"><CircleHelp size={20} /></span><h3>A little pause.</h3><p>{text}</p>{retry && <button className="button button-soft" onClick={retry} data-testid="button-retry">Try again <ArrowRight size={15} /></button>}</div>;
}
function LoadingGrid() {
  return <div className="work-grid" aria-label="Loading work">{[1, 2, 3].map((n) => <div className="skeleton-work" key={n}><div /><span /><i /></div>)}</div>;
}
function EmptyState({ title, copy, action }: { title: string; copy: string; action?: ReactNode }) {
  return <div className="state-panel empty-state"><span className="state-mark"><Sparkles size={20} /></span><h3>{title}</h3><p>{copy}</p>{action}</div>;
}
function PageTitle({ eyebrow, title, subtitle, side }: { eyebrow: string; title: string; subtitle?: string; side?: ReactNode }) {
  return <div className="page-title"><div><p className="eyebrow">{eyebrow}</p><h1 className="display-font">{title}</h1>{subtitle && <p className="page-subtitle">{subtitle}</p>}</div>{side && <div className="title-side">{side}</div>}</div>;
}
function WorkCard({ post, index = 0 }: { post: Post; index?: number }) {
  const artClass = `art-artwork art-tone-${index % 5}`;
  return <article className={`work-card ${index % 4 === 1 ? 'work-card-tall' : ''}`} data-testid={`card-post-${post.id}`}>
    <Link href={`/post/${post.id}`} className={artClass}>
      {post.media_path ? post.media_type?.startsWith('video') ? <video src={post.media_path} muted preload="metadata" /> : <img src={post.media_path} alt={post.title} loading="lazy" /> :
        <span className="text-art"><small>{post.category}</small><strong>{post.title}</strong><i>{post.creator_department}</i></span>}
      <span className="image-index">{String(post.id).padStart(2, '0')}</span>
      {post.featured && <span className="featured-tag"><Star size={11} fill="currentColor" /> On the wall</span>}
    </Link>
    <div className="work-card-copy">
      <div className="work-meta"><Link href={`/profile/${post.user_id}`} className="creator-mini"><Avatar src={post.creator_pic} name={post.creator_name} size="sm" /><span>{post.creator_name}</span></Link><span>{post.category}</span></div>
      <Link href={`/post/${post.id}`} className="work-title">{post.title}</Link>
      <div className="work-stats"><span><Heart size={14} /> {post.like_count}</span><span><MessageCircle size={14} /> {post.comment_count}</span><span><Eye size={14} /> {post.views}</span></div>
    </div>
  </article>;
}
function PostResults({ posts, loading, error, retry, emptyTitle = 'Nothing on this page yet', emptyCopy = 'Try another category or come back soon.' }: { posts?: Post[]; loading: boolean; error: boolean; retry: () => void; emptyTitle?: string; emptyCopy?: string }) {
  if (loading) return <LoadingGrid />;
  if (error) return <ErrorNotice retry={retry} />;
  if (!posts?.length) return <EmptyState title={emptyTitle} copy={emptyCopy} />;
  return <div className="work-grid">{posts.map((post, index) => <WorkCard post={post} index={index} key={post.id} />)}</div>;
}
function Header({ user }: { user: User | null }) {
  const [location] = useLocation();
  const [logoutOpen, setLogoutOpen] = useState(false);
  const logout = useLogout(mutRequest());
  const cache = useQueryClient();
  const signOut = () => logout.mutate(undefined, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetSessionQueryKey() }); setLogoutOpen(false); } });
  return <>
    <header className="topbar">
      <div className="header-inner">
        <Link href="/" className="brand-mark"><span className="brand-symbol">C<span>C</span></span><span className="brand-name">CampusCanvas<small>MES Kalladi College</small></span></Link>
        <nav className="desktop-nav" aria-label="Main navigation">{navItems.map(({ href, label, icon: Icon }) => <Link href={href} key={href} className={`nav-link ${location === href ? 'nav-active' : ''}`}><Icon size={16} />{label}</Link>)}{user?.role === 'admin' && <Link href="/admin" className={`nav-link ${location === '/admin' ? 'nav-active' : ''}`}><ShieldCheck size={16} />Moderation</Link>}</nav>
        <div className="header-actions"><Link href="/upload" className="button button-primary header-submit"><Plus size={16} /> Share your work</Link>
          {user ? <div className="profile-menu"><Link href="/profile" className="user-chip"><Avatar src={user.profile_pic} name={user.name} size="sm" /><span>{user.name.split(' ')[0]}</span></Link><button className="icon-button" aria-label="Sign out" onClick={() => setLogoutOpen(!logoutOpen)}><ChevronDown size={15} /></button>{logoutOpen && <div className="menu-pop"><button onClick={signOut}><LogOut size={15} /> Sign out</button></div>}</div> :
            <Link className="header-login" href="/login"><LogIn size={16} /> Sign in</Link>}
        </div>
      </div>
    </header>
    <nav className="mobile-nav" aria-label="Mobile navigation">{navItems.map(({ href, label, icon: Icon }) => <Link href={href} key={href} className={location === href ? 'mobile-active' : ''}><Icon size={19} /><span>{label === 'Campus events' ? 'Events' : label}</span></Link>)}{user?.role === 'admin' ? <Link href="/admin" className={location === '/admin' ? 'mobile-active' : ''}><ShieldCheck size={19} /><span>Moderate</span></Link> : <Link href={user ? '/profile' : '/login'} className={location.startsWith('/profile') ? 'mobile-active' : ''}><UserRound size={19} /><span>{user ? 'Portfolio' : 'Sign in'}</span></Link>}</nav>
  </>;
}
function Shell({ children }: { children: ReactNode }) {
  const session = useGetSession();
  csrfToken = session.data?.csrf_token ?? '';
  const user = session.data?.user ?? null;
  return <div className="app-shell grain"><Header user={user} /><main className="main-content page-enter">{children}</main><footer className="site-footer"><span className="footer-brand"><span className="brand-symbol small-symbol">C<span>C</span></span> Made on campus, shared with care.</span><span>MES Kalladi College · Creative community</span></footer></div>;
}

function HomePage() {
  const params = { sort: 'featured' as const, limit: 12 };
  const query = useGetPosts(params);
  const trending = useGetPosts({ sort: 'trending', limit: 4 });
  return <div className="home-page">
    <section className="hero-panel">
      <div className="hero-copy"><p className="hero-kicker"><span /> A campus full of ideas</p><h1 className="display-font">Good work<br />finds its people.</h1><p>Student-made art, words, photographs, sounds and films — all from right here at MES Kalladi.</p><div className="hero-actions"><Link href="/explore" className="button button-orange">Find your next favourite <ArrowRight size={16} /></Link><Link href="/upload" className="hero-text-link">Put your work out there <ArrowUpRight size={15} /></Link></div></div>
      <div className="hero-art" aria-hidden="true"><div className="hero-orbit orbit-one" /><div className="hero-orbit orbit-two" /><div className="hero-stamp"><span>MES</span><b>KALLADI<br />COLLEGE</b><small>ARTS · IDEAS · PEOPLE</small></div><div className="hero-note">There’s room<br />for your voice.</div><Sparkles className="hero-spark spark-a" size={25} /><Sparkles className="hero-spark spark-b" size={19} /></div>
      <div className="hero-bottom"><span>01 / 05</span><span>THE CAMPUS CREATIVE INDEX</span><span>Since this semester <ArrowDown size={13} /></span></div>
    </section>
    <section className="section-block"><div className="section-heading"><div><p className="eyebrow">Selected from our community</p><h2 className="display-font">Featured work</h2></div><Link href="/explore" className="quiet-link">See everything <ArrowRight size={15} /></Link></div><PostResults posts={query.data} loading={query.isLoading} error={query.isError} retry={() => query.refetch()} emptyTitle="The gallery is ready for its first story" emptyCopy="Be the first to share something you’ve made." /></section>
    <section className="home-lower">
      <div className="trending-teaser"><div className="section-heading compact"><div><p className="eyebrow">What’s finding an audience</p><h2 className="display-font">In the conversation</h2></div><Link href="/trending" className="quiet-link">All trending <ArrowRight size={15} /></Link></div>
        {trending.isLoading ? <div className="skeleton-list"><i /><i /><i /></div> : trending.isError ? <ErrorNotice retry={() => trending.refetch()} /> : trending.data?.length ? <div className="mini-work-list">{trending.data.slice(0, 3).map((p, i) => <Link className="mini-work" href={`/post/${p.id}`} key={p.id}><span className="mini-number">0{i + 1}</span><span className={`mini-thumb art-tone-${i}`}><span>{p.category.slice(0, 1)}</span></span><span className="mini-copy"><small>{p.category} · {p.creator_name}</small><b>{p.title}</b></span><span className="mini-likes"><Heart size={14} />{p.like_count}</span></Link>)}</div> : <p className="quiet-copy">The next favourite might be yours.</p>}
      </div>
      <aside className="event-callout"><div className="callout-top"><CalendarDays size={19} /><span>On campus</span><ArrowUpRight size={16} /></div><p className="eyebrow">Gather, make, share</p><h2 className="display-font">There’s more<br />happening here.</h2><p>Find the open calls, competitions and small gatherings that bring campus creatives together.</p><Link href="/events" className="button button-on-dark">Explore events <ArrowRight size={15} /></Link><div className="callout-loop" /></aside>
    </section>
  </div>;
}

function ExplorePage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All work');
  const [sort, setSort] = useState<'latest' | 'trending' | 'featured'>('latest');
  const params = useMemo(() => ({ ...(query.trim() ? { q: query.trim() } : {}), ...(category !== 'All work' ? { category } : {}), sort, limit: 30 }), [query, category, sort]);
  const posts = useGetPosts(params);
  const creators = useGetCreators(query.trim() ? { q: query.trim() } : undefined);
  return <div className="content-page">
    <PageTitle eyebrow="A little bit of everything" title="Explore the gallery" subtitle="Follow a thread. Find a new favourite. Meet the person behind it." />
    <div className="explore-tools"><label className="search-box"><Search size={18} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search work, people, or ideas…" aria-label="Search campus work" data-testid="input-explore-search" />{query && <button onClick={() => setQuery('')} aria-label="Clear search"><X size={15} /></button>}</label><label className="sort-control"><span>Sort by</span><select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort work" data-testid="select-sort"><option value="latest">Latest</option><option value="trending">Trending</option><option value="featured">Featured</option></select><ChevronDown size={14} /></label></div>
    <div className="category-row" role="group" aria-label="Filter by category">{categories.map((c) => <button className={`category-pill ${category === c ? 'selected' : ''}`} onClick={() => setCategory(c)} key={c} data-testid={`filter-${c.toLowerCase().replaceAll(' ', '-')}`}>{c}</button>)}</div>
    {query.trim() && creators.isError && <p className="search-note">Creator search is having a moment. You can still browse the work below.</p>}
    {query.trim() && creators.data?.length ? <div className="creator-results"><span className="eyebrow">People in the mix</span><div>{creators.data.slice(0, 5).map((person) => <Link href={`/profile/${person.id}`} className="creator-result" key={person.id}><Avatar src={person.profile_pic} name={person.name} size="sm" /><span>{person.name}<small>{person.department}</small></span><ArrowUpRight size={14} /></Link>)}</div></div> : null}
    <div className="result-heading"><span>{posts.data?.length ?? 0} works</span><span>{category}{query ? ` · “${query}”` : ''}</span></div>
    <PostResults posts={posts.data} loading={posts.isLoading} error={posts.isError} retry={() => posts.refetch()} emptyTitle="No work found on that path" emptyCopy="Try a different search, or start with another category." />
  </div>;
}
function TrendingPage() {
  const query = useGetPosts({ sort: 'trending', limit: 30 });
  const posts = query.data ?? [];
  return <div className="content-page"><PageTitle eyebrow="The campus pulse" title="Finding its people" subtitle="Work getting shared, saved and talked about across the college." /><div className="trend-banner"><span className="trend-symbol"><TrendingUp size={24} /></span><div><b>Growing conversations</b><p>Ranked by the community’s recent appreciation and discussion.</p></div><span className="trend-period">THIS WEEK</span></div>
    {query.isLoading ? <LoadingGrid /> : query.isError ? <ErrorNotice retry={() => query.refetch()} /> : posts.length ? <div className="ranked-list">{posts.map((post, index) => <div className="ranked-row" key={post.id}><span className="rank-number">{String(index + 1).padStart(2, '0')}</span><WorkCard post={post} index={index} /><div className="rank-note"><TrendingUp size={15} /><b>{post.like_count + post.comment_count}</b><small>moments of appreciation</small></div></div>)}</div> : <EmptyState title="A quiet moment before the next wave" copy="Once people start discovering work, the campus pulse will show up here." />}</div>;
}

function EventCard({ event }: { event: Event }) {
  const request = mutRequest();
  const entry = useEnterEvent(request);
  const session = useGetSession();
  const cache = useQueryClient();
  const [error, setError] = useState('');
  const date = event.event_date ? new Date(event.event_date) : null;
  const onEnter = () => { if (!session.data?.user) return; entry.mutate({ eventId: event.id, data: {} }, { onSuccess: () => cache.invalidateQueries({ queryKey: getGetEventsQueryKey() }), onError: (err) => setError(err.message) }); };
  return <article className="event-card" data-testid={`card-event-${event.id}`}><div className="event-date"><b>{date ? date.toLocaleDateString('en', { day: '2-digit' }) : '—'}</b><span>{date ? date.toLocaleDateString('en', { month: 'short' }).toUpperCase() : 'CAMPUS'}</span></div><div className="event-info"><div className="event-type">{event.type}<span>·</span><span>{event.entry_count} {event.entry_count === 1 ? 'person joining' : 'people joining'}</span></div><h3>{event.title}</h3><p>{event.description}</p><div className="event-location">{event.location && <><MapPin size={14} />{event.location}</>}{date && <><Clock3 size={14} />{date.toLocaleString('en', { dateStyle: 'medium', timeStyle: 'short' })}</>}</div>{error && <p className="form-error">{error}</p>}{event.type === 'competition' && !session.data?.user && <Link className="event-signin" href="/login">Sign in to enter</Link>}</div>{event.type === 'competition' && <button className={`button ${event.entered ? 'button-soft' : 'button-primary'} event-enter`} onClick={onEnter} disabled={!session.data?.user || event.entered || entry.isPending} data-testid={`button-enter-event-${event.id}`}>{entry.isPending ? 'Joining…' : event.entered ? <><Check size={15} /> I’m in</> : 'Count me in'}</button>}</article>;
}
function EventsPage() {
  const events = useGetEvents();
  const session = useGetSession();
  const [showCreate, setShowCreate] = useState(false);
  return <div className="content-page"><PageTitle eyebrow="Beyond the studio" title="Around campus" subtitle="Open calls, creative meetups and announcements from the MES Kalladi community." side={session.data?.user?.role === 'admin' ? <button className="button button-primary" onClick={() => setShowCreate(!showCreate)}><Plus size={16} /> Post an announcement</button> : undefined} />
    {showCreate && <CreateEventForm onClose={() => setShowCreate(false)} />}
    {events.isLoading ? <div className="skeleton-list"><i /><i /><i /></div> : events.isError ? <ErrorNotice retry={() => events.refetch()} /> : events.data?.length ? <div className="events-list">{events.data.map((event) => <EventCard key={event.id} event={event} />)}</div> : <EmptyState title="A little breathing room" copy="No events have been announced yet. Check back when something’s brewing." />}
  </div>;
}
function CreateEventForm({ onClose }: { onClose: () => void }) {
  const create = useCreateEvent(mutRequest());
  const cache = useQueryClient();
  const [error, setError] = useState('');
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const rawDate = String(f.get('event_date') || ''); create.mutate({ data: { title: String(f.get('title')), description: String(f.get('description')), type: String(f.get('type')) as 'event' | 'competition' | 'announcement', event_date: rawDate ? new Date(rawDate).toISOString() : null, location: String(f.get('location') || '') } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetEventsQueryKey() }); onClose(); }, onError: (err) => setError(err.message) }); };
  return <form className="form-panel event-create-form" onSubmit={submit}><div className="form-head"><div><p className="eyebrow">Share with the campus</p><h3>New announcement</h3></div><button type="button" className="icon-button" onClick={onClose} aria-label="Close"><X size={18} /></button></div><div className="form-grid"><label>Title<input name="title" required minLength={3} maxLength={120} /></label><label>Type<select name="type"><option value="event">Event</option><option value="competition">Competition</option><option value="announcement">Announcement</option></select></label><label className="wide-field">What should people know?<textarea name="description" required minLength={3} maxLength={3000} rows={3} /></label><label>Date and time<input name="event_date" type="datetime-local" /></label><label>Location<input name="location" maxLength={200} /></label></div>{error && <p className="form-error">{error}</p>}<button className="button button-primary" disabled={create.isPending}>{create.isPending ? 'Publishing…' : 'Publish announcement'} <ArrowRight size={15} /></button></form>;
}

function UploadPage() {
  const session = useGetSession();
  const create = useCreatePost(mutRequest());
  const cache = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); const category = String(f.get('category')); const description = String(f.get('description') || ''); const tags = String(f.get('tags') || ''); const textBody = String(f.get('text_body') || '');
    create.mutate({ data: { title: String(f.get('title')), category, description, tags, ...(file ? { media: file } : {}), ...(category === 'Writing' ? { text_body: textBody } : {}) } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetPostsQueryKey() }); setDone(true); }, onError: (err) => setError(err.message) }); };
  if (!session.data?.user) return <SignedOut prompt="Sign in before you share your work." />;
  if (done) return <div className="upload-success"><span className="success-seal"><Check size={27} /></span><p className="eyebrow">Submission received</p><h1 className="display-font">Your work is<br />in good hands.</h1><p>It’s been sent to the campus team for review. Once approved, your work will be ready to find its people.</p><div><Link className="button button-primary" href="/explore">Back to the gallery <ArrowRight size={15} /></Link><Link href="/profile" className="quiet-link">Visit your portfolio</Link></div></div>;
  return <div className="upload-page"><div className="upload-intro"><p className="eyebrow">Make something visible</p><h1 className="display-font">Add to the<br />campus story.</h1><p>Your work doesn’t need to be finished, famous or perfect. It just needs to be yours.</p><div className="upload-side-note"><span>01</span><p>Thoughtful work.<br />Supportive audience.<br />Room to grow.</p></div></div>
    <form className="upload-form" onSubmit={submit}><div className="form-head"><div><p className="eyebrow">New submission</p><h2>Tell us about it</h2></div><span className="review-badge"><ShieldCheck size={15} /> Reviewed before publishing</span></div>
      <label className="form-field">Title<input name="title" required maxLength={120} placeholder="Give your work a name" data-testid="input-post-title" /></label>
       <label className="form-field">Category<select name="category" required value={category} onChange={(e) => setCategory(e.target.value)}><option value="" disabled>Choose a creative practice</option>{categories.slice(1).map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
      <label className="form-field">A few words about it <span className="optional">(optional)</span><textarea name="description" maxLength={5000} rows={4} placeholder="What inspired this? What should people notice?" data-testid="input-post-description" /></label>
      <label className="form-field">Tags <span className="optional">(separate with commas)</span><input name="tags" maxLength={300} placeholder="watercolour, campus life, short film" /></label>
       {(category === 'Writing' || category === 'Poetry') && <label className="form-field">Written work excerpt <span className="optional">(optional)</span><textarea name="text_body" maxLength={20000} rows={5} placeholder="Paste a poem, story, article or excerpt…" /></label>}
       <label className={`file-drop ${file ? 'file-attached' : ''}`}><input type="file" accept="image/*,video/*,audio/*,.pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} data-testid="input-upload-media" /><span className="file-icon"><ImagePlus size={21} /></span><b>{file ? file.name : 'Add a piece of the work'}</b><small>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB · ready to attach` : 'Image, video, audio, PDF, DOCX or TXT · up to the upload limit'}</small>{file && <button type="button" className="file-remove" onClick={(e) => { e.preventDefault(); setFile(null); }} aria-label="Remove file"><X size={15} /></button>}</label>
      {error && <p className="form-error">{error}</p>}<button type="submit" className="button button-primary submit-wide" disabled={create.isPending}>{create.isPending ? 'Sending for review…' : 'Submit for review'} <ArrowRight size={16} /></button><p className="form-footnote">By submitting, you confirm that this is your work and that you’re happy to share it with the college community.</p>
    </form></div>;
}

function SignedOut({ prompt = 'Sign in to join the CampusCanvas community.' }: { prompt?: string }) {
  return <div className="signed-out-panel"><span className="state-mark"><UserRound size={21} /></span><p className="eyebrow">Your place is here</p><h2 className="display-font">{prompt}</h2><p>Student and faculty accounts from MES Kalladi College are welcome.</p><div><Link href="/login" className="button button-primary">Sign in <ArrowRight size={15} /></Link><Link href="/register" className="quiet-link">Create an account</Link></div></div>;
}
function PostPage() {
  const params = useParams<{ postId: string }>();
  const postId = Number(params.postId);
  const postQuery = useGetPost(postId, { query: { enabled: Number.isFinite(postId), queryKey: getGetPostQueryKey(postId) } });
  const session = useGetSession();
  const like = useToggleLike(mutRequest());
  const bookmark = useToggleBookmark(mutRequest());
  const comment = useAddComment(mutRequest());
  const report = useReportPost(mutRequest());
  const shareMutation = useSharePost(mutRequest());
  const cache = useQueryClient();
  const [commentText, setCommentText] = useState('');
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState('');
  const [notice, setNotice] = useState('');
  const refresh = () => cache.invalidateQueries({ queryKey: getGetPostQueryKey(postId) });
  const detail = postQuery.data;
  const post = detail?.post;
  const act = (kind: 'like' | 'bookmark') => {
    if (kind === 'like') like.mutate({ postId }, { onSuccess: () => { refresh(); cache.invalidateQueries({ queryKey: getGetPostsQueryKey() }); } });
    else bookmark.mutate({ postId }, { onSuccess: () => { refresh(); cache.invalidateQueries({ queryKey: getGetBookmarksQueryKey() }); setNotice('Saved to your bookmarks.'); } });
  };
  const sendComment = (e: FormEvent) => { e.preventDefault(); comment.mutate({ postId, data: { text: commentText.trim() } }, { onSuccess: () => { setCommentText(''); refresh(); } }); };
  const sendReport = (e: FormEvent) => { e.preventDefault(); report.mutate({ postId, data: { reason: reportReason } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetAdminReportsQueryKey() }); setShowReport(false); setNotice('Thanks for helping us keep this space thoughtful.'); } }); };
  const share = async () => { const url = window.location.href; shareMutation.mutate({ postId }, { onSuccess: () => { refresh(); cache.invalidateQueries({ queryKey: getGetPostsQueryKey() }); } }); try { if (navigator.share) await navigator.share({ title: post?.title, url }); else { await navigator.clipboard.writeText(url); setNotice('Link copied to clipboard.'); } } catch { setNotice('Sharing was cancelled.'); } };
  if (postQuery.isLoading) return <div className="content-page"><div className="skeleton-work detail-skeleton" /></div>;
  if (postQuery.isError || !detail) return <div className="content-page"><ErrorNotice retry={() => postQuery.refetch()} text="This work may have moved, or may not be available." /></div>;
  return <div className="post-detail-page"><Link href="/explore" className="back-link"><ArrowLeft size={15} /> Back to the gallery</Link><div className="post-detail-grid"><article className="post-main">
    <div className={`post-media art-artwork art-tone-${post!.id % 5}`}>{post!.media_path ? post!.media_type?.startsWith('video') ? <video src={post!.media_path} controls /> : post!.media_type?.startsWith('audio') ? <audio src={post!.media_path} controls /> : <img src={post!.media_path} alt={post!.title} /> : <div className="text-art detail-art"><small>{post!.category}</small><strong>{post!.title}</strong><i>{post!.creator_department}</i></div>}</div>
    <div className="post-story"><div className="post-category-label">{post!.category} {post!.featured && <span><Star size={12} fill="currentColor" /> Featured</span>}</div><h1 className="display-font">{post!.title}</h1><p className="post-description">{post!.description}</p><div className="tag-list">{post!.tags?.split(',').filter(Boolean).map((tag) => <span key={tag}>#{tag.trim()}</span>)}</div>
      <div className="post-actions"><button className={post!.liked ? 'action-on' : ''} onClick={() => act('like')} disabled={!session.data?.user || like.isPending} data-testid="button-like"><Heart size={17} fill={post!.liked ? 'currentColor' : 'none'} /> Appreciate <b>{post!.like_count}</b></button><button className={post!.bookmarked ? 'action-on' : ''} onClick={() => act('bookmark')} disabled={!session.data?.user || bookmark.isPending} data-testid="button-bookmark"><Bookmark size={17} fill={post!.bookmarked ? 'currentColor' : 'none'} /> Save</button><button onClick={share} disabled={shareMutation.isPending} data-testid="button-share"><ArrowUpRight size={17} /> Share <b>{post!.share_count ?? 0}</b></button><button onClick={() => setShowReport(!showReport)} data-testid="button-report"><Flag size={16} /> Report</button></div>
      {notice && <p className="inline-notice"><Check size={15} />{notice}<button onClick={() => setNotice('')} aria-label="Dismiss"><X size={14} /></button></p>}
       {showReport && (session.data?.user ? <form className="report-box" onSubmit={sendReport}><label>What should the campus team know?<textarea required minLength={3} maxLength={500} value={reportReason} onChange={(e) => setReportReason(e.target.value)} placeholder="Share a specific concern…" /></label><button className="button button-primary" disabled={report.isPending}>{report.isPending ? 'Sending…' : 'Send report'}</button></form> : <p className="comments-signin"><Link href="/login">Sign in</Link> to report a concern.</p>)}
    </div>
    <section className="comments-section"><div className="comments-heading"><div><p className="eyebrow">Keep it kind</p><h2 className="display-font">Notes from the community <span>{detail.comments.length}</span></h2></div></div>
      {session.data?.user ? <form className="comment-form" onSubmit={sendComment}><Avatar src={session.data.user.profile_pic} name={session.data.user.name} size="sm" /><input value={commentText} onChange={(e) => setCommentText(e.target.value)} placeholder="Say something thoughtful…" maxLength={1000} aria-label="Write a comment" data-testid="input-comment" /><button className="send-comment" type="submit" disabled={!commentText.trim() || comment.isPending} aria-label="Post comment" data-testid="button-comment"><Send size={17} /></button></form> : <p className="comments-signin"><Link href="/login">Sign in</Link> to leave a note.</p>}
      {detail.comments.length ? <div className="comment-list">{detail.comments.map((item) => <div className="comment-row" key={item.id}><Avatar src={item.user_pic} name={item.user_name} size="sm" /><div><div className="comment-by"><b>{item.user_name}</b><span>{new Date(item.created_at).toLocaleDateString()}</span></div><p>{item.text}</p></div></div>)}</div> : <div className="no-comments">The first note is waiting to be written.</div>}
    </section>
    </article><aside className="creator-sidebar"><p className="eyebrow">The person behind it</p><Link className="creator-feature" href={`/profile/${post!.user_id}`}><Avatar src={post!.creator_pic} name={post!.creator_name} size="lg" /><h3>{post!.creator_name}</h3><p>{post!.creator_department}</p><span>View portfolio <ArrowUpRight size={14} /></span></Link><div className="post-facts"><span><Eye size={15} /> {post!.views} views</span><span><Heart size={15} /> {post!.like_count} appreciations</span><span>Shared {new Date(post!.created_at).toLocaleDateString()}</span></div></aside></div></div>;
}

function ProfilePage() {
  const session = useGetSession();
  const me = useGetMyProfile({ query: { enabled: !!session.data?.user, queryKey: getGetMyProfileQueryKey() } });
  const update = useUpdateMyProfile(mutRequest());
  const avatar = useUploadAvatar(mutRequest());
  const cache = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState('');
  const user = me.data;
  if (!session.data?.user && !session.isLoading) return <div className="content-page"><SignedOut prompt="A portfolio starts with you." /></div>;
  if (me.isLoading || session.isLoading) return <div className="content-page"><div className="profile-loading" /></div>;
  if (me.isError || !user) return <div className="content-page"><ErrorNotice retry={() => me.refetch()} /></div>;
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const f = new FormData(e.currentTarget); update.mutate({ data: { name: String(f.get('name')), department: String(f.get('department')), bio: String(f.get('bio')), skills: String(f.get('skills')) } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetMyProfileQueryKey() }); cache.invalidateQueries({ queryKey: getGetSessionQueryKey() }); setEditing(false); }, onError: (err) => setError(err.message) }); };
  return <div className="profile-page"><div className="profile-cover"><div className="cover-orbit" /><span>MES KALLADI · CREATOR DIRECTORY</span><div className="profile-avatar-wrap"><Avatar src={user.profile_pic} name={user.name} size="lg" /><label className="avatar-upload" title="Update profile photo"><Camera size={15} /><input type="file" accept="image/*" aria-label="Upload profile photo" onChange={(e) => { const file = e.target.files?.[0]; if (file) avatar.mutate({ data: { media: file } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetMyProfileQueryKey() }); cache.invalidateQueries({ queryKey: getGetSessionQueryKey() }); }, onError: (err) => setError(err.message) }); }} /></label></div></div><div className="profile-content"><div className="profile-title-row"><div><p className="eyebrow">{user.role} · {user.department}</p><h1 className="display-font">{user.name}</h1></div><button className="button button-soft" onClick={() => setEditing(!editing)}><PenLine size={15} /> {editing ? 'Close editor' : 'Edit portfolio'}</button></div>
    {error && !editing && <p className="form-error">{error}</p>}
    {avatar.isPending && <p className="inline-notice"><Camera size={14} />Updating your profile photo…</p>}
    {editing && <form className="form-panel profile-edit-form" onSubmit={submit}><h3>Your profile, your words</h3><div className="form-grid"><label>Name<input name="name" defaultValue={user.name} maxLength={80} required /></label><label>Department<input name="department" defaultValue={user.department} maxLength={120} /></label><label className="wide-field">A short bio<textarea name="bio" defaultValue={user.bio} maxLength={500} rows={3} /></label><label className="wide-field">Creative practices <span className="optional">(comma-separated)</span><input name="skills" defaultValue={user.skills || ''} maxLength={300} /></label></div>{error && <p className="form-error">{error}</p>}<button className="button button-primary" disabled={update.isPending}>{update.isPending ? 'Saving…' : 'Save changes'} <Check size={15} /></button></form>}
    <div className="profile-bio-row"><p>{user.bio || 'A new chapter, waiting to be written.'}</p><div className="profile-counts"><span><b>{user.post_count ?? 0}</b><small>works</small></span><span><b>{user.follower_count ?? 0}</b><small>following this work</small></span></div></div>
    {user.skills && <div className="tag-list profile-skills">{user.skills.split(',').filter(Boolean).map((skill) => <span key={skill}>{skill.trim()}</span>)}</div>}
    <div className="section-heading profile-work-heading"><div><p className="eyebrow">A growing collection</p><h2 className="display-font">Your work</h2></div><div className="profile-work-actions"><Link href="/bookmarks" className="button button-soft"><Bookmark size={15} /> Saved work</Link><Link href="/upload" className="button button-primary"><Plus size={15} /> Add a work</Link></div></div>
     {user.id ? <UserPosts userId={user.id} /> : null}
  </div></div>;
}
function UserPosts({ userId }: { userId: number }) {
  const profile = useGetUserProfile(userId, { query: { queryKey: getGetUserProfileQueryKey(userId) } });
  if (profile.isLoading) return <LoadingGrid />;
  if (profile.isError) return <ErrorNotice retry={() => profile.refetch()} />;
  return profile.data?.posts.length ? <div className="work-grid">{profile.data.posts.map((post, i) => <WorkCard post={post} index={i} key={post.id} />)}</div> : <EmptyState title="Your first work belongs here" copy="Share something you’ve made and start building your campus portfolio." action={<Link href="/upload" className="button button-primary">Share a work <ArrowRight size={15} /></Link>} />;
}
function BookmarksPage() {
  const session = useGetSession();
  const bookmarks = useGetBookmarks({ query: { enabled: !!session.data?.user, queryKey: getGetBookmarksQueryKey() } });
  if (session.isLoading) return <div className="content-page"><div className="profile-loading" /></div>;
  if (!session.data?.user) return <div className="content-page"><SignedOut prompt="Keep the work you want to come back to." /></div>;
  return <div className="content-page"><PageTitle eyebrow="A collection for later" title="Saved work" subtitle="Pieces you’ve bookmarked from around campus." />{bookmarks.isLoading ? <LoadingGrid /> : bookmarks.isError ? <ErrorNotice retry={() => bookmarks.refetch()} /> : bookmarks.data?.length ? <div className="work-grid">{bookmarks.data.map((post, i) => <WorkCard post={post} index={i} key={post.id} />)}</div> : <EmptyState title="Nothing tucked away yet" copy="Bookmark a work that speaks to you and it’ll be waiting here." action={<Link href="/explore" className="button button-primary">Explore work <ArrowRight size={15} /></Link>} />}</div>;
}
function CreatorProfilePage() {
  const params = useParams<{ userId: string }>();
  const userId = Number(params.userId);
  const profile = useGetUserProfile(userId, { query: { enabled: Number.isFinite(userId), queryKey: getGetUserProfileQueryKey(userId) } });
  const session = useGetSession();
  const follow = useToggleFollow(mutRequest());
  const cache = useQueryClient();
  if (profile.isLoading) return <div className="content-page"><div className="profile-loading" /></div>;
  if (profile.isError || !profile.data) return <div className="content-page"><ErrorNotice retry={() => profile.refetch()} /></div>;
  const { user, posts } = profile.data;
  const self = session.data?.user?.id === user.id;
  return <div className="profile-page creator-profile"><div className="profile-cover"><div className="cover-orbit" /><span>MES KALLADI · CREATOR DIRECTORY</span><div className="profile-avatar-wrap"><Avatar src={user.profile_pic} name={user.name} size="lg" /></div></div><div className="profile-content"><div className="profile-title-row"><div><p className="eyebrow">{user.role} · {user.department}</p><h1 className="display-font">{user.name}</h1></div>{!self && <button className={`button ${user.following ? 'button-soft' : 'button-primary'}`} disabled={!session.data?.user || follow.isPending} onClick={() => follow.mutate({ userId }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetUserProfileQueryKey(userId) }); cache.invalidateQueries({ queryKey: getGetCreatorsQueryKey() }); } })} data-testid="button-follow"><Users size={15} />{user.following ? 'Following' : 'Follow'}</button>}{self && <Link href="/profile" className="button button-soft">Your portfolio <ArrowRight size={15} /></Link>}</div><div className="profile-bio-row"><p>{user.bio || 'A creative mind from the MES Kalladi community.'}</p><div className="profile-counts"><span><b>{posts.length}</b><small>works</small></span><span><b>{profile.data.follower_count}</b><small>followers</small></span><span><b>{profile.data.following_count}</b><small>following</small></span></div></div>{user.skills && <div className="tag-list profile-skills">{user.skills.split(',').filter(Boolean).map((skill) => <span key={skill}>{skill.trim()}</span>)}</div>}<div className="section-heading profile-work-heading"><div><p className="eyebrow">From this creator</p><h2 className="display-font">Selected work</h2></div></div>{posts.length ? <div className="work-grid">{posts.map((post, i) => <WorkCard post={post} index={i} key={post.id} />)}</div> : <EmptyState title="The canvas is still opening" copy="This creator hasn’t shared a piece of work yet." />}</div></div>;
}

function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const isRegister = mode === 'register';
  const login = useLogin(mutRequest());
  const register = useRegister(mutRequest());
  const cache = useQueryClient();
  const [, setLocation] = useLocation();
  const [error, setError] = useState('');
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); setError(''); const f = new FormData(e.currentTarget);
    if (isRegister) register.mutate({ data: { name: String(f.get('name')), email: String(f.get('email')), password: String(f.get('password')), department: String(f.get('department')), role: String(f.get('role')) as 'student' | 'faculty' } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetSessionQueryKey() }); setLocation('/profile'); }, onError: (err) => setError(err.message) });
    else login.mutate({ data: { email: String(f.get('email')), password: String(f.get('password')) } }, { onSuccess: () => { cache.invalidateQueries({ queryKey: getGetSessionQueryKey() }); setLocation('/'); }, onError: (err) => setError(err.message) });
  };
  const pending = login.isPending || register.isPending;
  return <div className="auth-page"><div className="auth-story"><Link href="/" className="brand-mark"><span className="brand-symbol">C<span>C</span></span><span className="brand-name">CampusCanvas<small>MES Kalladi College</small></span></Link><div><p className="eyebrow">For the makers and the curious</p><h1 className="display-font">A place for<br />what you make.</h1><p>Find your people. Give your work a home. See what the rest of campus is creating.</p></div><span className="auth-foot">STUDENT & FACULTY COMMUNITY · MES KALLADI</span><div className="auth-graphic"><div /><div /><span>CC</span></div></div>
    <div className="auth-form-side"><Link href="/" className="auth-back"><ArrowLeft size={15} /> Back to CampusCanvas</Link><form className="auth-form" onSubmit={submit}><p className="eyebrow">{isRegister ? 'Start your portfolio' : 'Welcome back'}</p><h2 className="display-font">{isRegister ? 'Make a little room.' : 'Good to see you.'}</h2><p>{isRegister ? 'Join the creative community at MES Kalladi College.' : 'Pick up where campus left off.'}</p>
      {isRegister && <><label>Your name<input name="name" required minLength={2} maxLength={80} placeholder="Your full name" data-testid="input-register-name" /></label><label>Department<input name="department" required minLength={2} maxLength={120} placeholder="e.g. English" data-testid="input-register-department" /></label><label>I’m here as<select name="role" defaultValue="student"><option value="student">Student</option><option value="faculty">Faculty</option></select></label></>}
      <label>Email address<input type="email" name="email" required maxLength={254} placeholder="you@example.com" data-testid="input-auth-email" /></label><label>Password<input type="password" name="password" required minLength={isRegister ? 10 : 1} maxLength={128} placeholder={isRegister ? 'At least 10 characters' : 'Your password'} data-testid="input-auth-password" /></label>
      {error && <p className="form-error">{error}</p>}<button type="submit" className="button button-primary auth-submit" disabled={pending}>{pending ? 'One moment…' : isRegister ? 'Create your account' : 'Sign in'} <ArrowRight size={16} /></button><p className="auth-switch">{isRegister ? 'Already part of the community?' : 'New to CampusCanvas?'} <Link href={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</Link></p><p className="privacy-note">This is a campus community for students and faculty of MES Kalladi College.</p>
    </form></div></div>;
}

function AdminPage() {
  const session = useGetSession();
  const summary = useGetAdminSummary();
  const posts = useGetAdminPosts({ status: 'pending' });
  const reports = useGetAdminReports();
  const users = useGetAdminUsers();
  const moderate = useModeratePost(mutRequest());
  const resolve = useResolveReport(mutRequest());
  const setStatus = useSetUserStatus(mutRequest());
  const cache = useQueryClient();
  const [tab, setTab] = useState<'posts' | 'reports' | 'users'>('posts');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  if (session.isLoading) return <div className="content-page"><div className="profile-loading" /></div>;
  if (session.data?.user?.role !== 'admin') return <div className="content-page"><div className="admin-denied"><ShieldCheck size={30} /><p className="eyebrow">A quieter corner</p><h1 className="display-font">Staff access only.</h1><p>The moderation desk is reserved for CampusCanvas administrators.</p><Link href="/" className="button button-primary">Return to the gallery <ArrowRight size={15} /></Link></div></div>;
  const refreshAdmin = () => { cache.invalidateQueries({ queryKey: getGetAdminSummaryQueryKey() }); cache.invalidateQueries({ queryKey: getGetAdminPostsQueryKey({ status: 'pending' }) }); cache.invalidateQueries({ queryKey: getGetAdminReportsQueryKey() }); cache.invalidateQueries({ queryKey: getGetAdminUsersQueryKey() }); cache.invalidateQueries({ queryKey: getGetPostsQueryKey() }); };
  const moderatePost = (postId: number, status: 'approved' | 'rejected', featured = false) => moderate.mutate({ postId, data: { status, ...(status === 'approved' ? { featured } : {}), ...(note ? { note } : {}) } }, { onSuccess: refreshAdmin, onError: (err) => setError(err.message) });
  const queryError = summary.isError || posts.isError || reports.isError || users.isError;
  return <div className="admin-page content-page"><PageTitle eyebrow="The care behind the canvas" title="Moderation desk" subtitle="Keep the space welcoming, thoughtful and safe for everyone." />
    <div className="admin-stats">{summary.data ? <>{[['Awaiting review', summary.data.pending_posts], ['Open reports', summary.data.open_reports], ['Active creators', summary.data.active_users], ['Published works', summary.data.approved_posts], ['Campus notices', summary.data.events]].map(([name, value]) => <div className="admin-stat" key={name}><small>{name}</small><b>{value}</b></div>)}</> : summary.isLoading ? <div className="admin-stat-skeleton" /> : <ErrorNotice retry={() => summary.refetch()} />}</div>
    <div className="admin-tabs">{(['posts', 'reports', 'users'] as const).map((item) => <button className={tab === item ? 'admin-tab-active' : ''} key={item} onClick={() => setTab(item)}>{item === 'posts' ? <>For review <span>{summary.data?.pending_posts ?? 0}</span></> : item === 'reports' ? <>Reports <span>{summary.data?.open_reports ?? 0}</span></> : 'People'}</button>)}</div>
    {queryError && <ErrorNotice retry={() => { summary.refetch(); posts.refetch(); reports.refetch(); users.refetch(); }} />}
    <label className="moderation-note">Optional note for a decision<input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder="A brief private moderation note" /></label>
    {tab === 'posts' && (posts.isLoading ? <LoadingGrid /> : posts.data?.length ? <div className="moderation-list">{posts.data.map((post) => <article className="moderation-post" key={post.id}><div className={`moderation-thumb art-tone-${post.id % 5}`}>{post.media_path && post.media_type?.startsWith('image') ? <img src={post.media_path} alt="" /> : <Palette size={23} />}</div><div className="moderation-copy"><span className="eyebrow">{post.category} · {post.creator_name}</span><h3>{post.title}</h3><p>{post.description}</p><Link href={`/post/${post.id}`} className="quiet-link">Review submission <ArrowUpRight size={14} /></Link></div><div className="moderation-actions"><button className="button button-primary" disabled={moderate.isPending} onClick={() => moderatePost(post.id, 'approved')}><Check size={15} /> Approve</button><button className="button button-soft" disabled={moderate.isPending} onClick={() => moderatePost(post.id, 'approved', true)}><Star size={15} /> Feature</button><button className="button button-danger-soft" disabled={moderate.isPending} onClick={() => moderatePost(post.id, 'rejected')}><X size={15} /> Decline</button></div></article>)}</div> : <EmptyState title="The review queue is clear" copy="New submissions will appear here once they’re ready for a look." />)}
    {tab === 'reports' && (reports.isLoading ? <div className="skeleton-list"><i /><i /></div> : reports.data?.filter((r) => r.status === 'open').length ? <div className="admin-table"><div className="table-head"><span>Work & concern</span><span>Reported by</span><span>Received</span><span>Next step</span></div>{reports.data.filter((r) => r.status === 'open').map((report) => <div className="table-row report-row" key={report.id}><span><Link href={`/post/${report.post_id}`}>{report.post_title}</Link><small>{report.reason}</small></span><span>{report.reporter_name}</span><span>{new Date(report.created_at).toLocaleDateString()}</span><button className="button button-soft" disabled={resolve.isPending} onClick={() => resolve.mutate({ reportId: report.id }, { onSuccess: refreshAdmin, onError: (err) => setError(err.message) })}>Resolve <Check size={14} /></button></div>)}</div> : <EmptyState title="No open reports" copy="Thank you for keeping the community thoughtful." />)}
    {tab === 'users' && (users.isLoading ? <div className="skeleton-list"><i /><i /></div> : users.data?.length ? <div className="admin-table"><div className="table-head"><span>Creator</span><span>Department</span><span>Role</span><span>Access</span></div>{users.data.map((person) => <div className="table-row" key={person.id}><span className="table-person"><Avatar src={person.profile_pic} name={person.name} size="sm" /><b>{person.name}</b></span><span>{person.department}</span><span>{person.role}</span><button className={`button ${person.is_active ? 'button-danger-soft' : 'button-soft'}`} disabled={setStatus.isPending} onClick={() => setStatus.mutate({ userId: person.id, data: { is_active: !person.is_active } }, { onSuccess: refreshAdmin, onError: (err) => setError(err.message) })}>{person.is_active ? 'Pause access' : 'Restore access'}</button></div>)}</div> : <EmptyState title="No people to list" copy="The creator directory will appear here." />)}
    {error && <p className="form-error">{error}</p>}<div className="admin-event-link"><CalendarDays size={17} /><span><b>Campus events and notices</b><small>Publish a new event from the community calendar.</small></span><Link href="/events" className="button button-soft">Open events <ArrowRight size={14} /></Link></div>
  </div>;
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}
function Router() {
  const session = useGetSession();
  csrfToken = session.data?.csrf_token ?? '';
  return <RoutedErrorBoundary><Shell><Switch>
    <Route path="/" component={HomePage} />
    <Route path="/explore" component={ExplorePage} />
    <Route path="/trending" component={TrendingPage} />
    <Route path="/events" component={EventsPage} />
    <Route path="/upload" component={UploadPage} />
    <Route path="/post/:postId" component={PostPage} />
    <Route path="/profile" component={ProfilePage} />
    <Route path="/bookmarks" component={BookmarksPage} />
    <Route path="/profile/:userId" component={CreatorProfilePage} />
    <Route path="/login">{() => <AuthPage mode="login" />}</Route>
    <Route path="/register">{() => <AuthPage mode="register" />}</Route>
    <Route path="/admin" component={AdminPage} />
    <Route component={NotFound} />
  </Switch></Shell></RoutedErrorBoundary>;
}
function App() {
  return <QueryClientProvider client={queryClient}><TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}><Router /></WouterRouter><Toaster /></TooltipProvider></QueryClientProvider>;
}
export default App;
