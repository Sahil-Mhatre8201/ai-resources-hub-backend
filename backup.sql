--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: bookmarks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bookmarks (
    id integer NOT NULL,
    user_id integer,
    resource_type character varying,
    title character varying,
    description character varying,
    url character varying
);


ALTER TABLE public.bookmarks OWNER TO postgres;

--
-- Name: bookmarks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bookmarks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bookmarks_id_seq OWNER TO postgres;

--
-- Name: bookmarks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bookmarks_id_seq OWNED BY public.bookmarks.id;


--
-- Name: community_uploads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.community_uploads (
    id integer NOT NULL,
    title character varying NOT NULL,
    description character varying NOT NULL,
    resource_type character varying NOT NULL,
    status character varying,
    user_id integer NOT NULL,
    url character varying NOT NULL
);


ALTER TABLE public.community_uploads OWNER TO postgres;

--
-- Name: community_uploads_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.community_uploads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.community_uploads_id_seq OWNER TO postgres;

--
-- Name: community_uploads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.community_uploads_id_seq OWNED BY public.community_uploads.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    is_admin boolean
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: bookmarks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookmarks ALTER COLUMN id SET DEFAULT nextval('public.bookmarks_id_seq'::regclass);


--
-- Name: community_uploads id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_uploads ALTER COLUMN id SET DEFAULT nextval('public.community_uploads_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
65de94252810
\.


--
-- Data for Name: bookmarks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bookmarks (id, user_id, resource_type, title, description, url) FROM stdin;
17	3	research paper	User-based collaborative filtering approach for content recommendation\n  in OpenCourseWare platforms	  A content recommender system or a recommendation system represents a subclass\nof information filtering systems which seeks to predict the user preferences,\ni.e. the content that would be most likely positively "rated" by the user.\nNowadays, the recommender systems of OpenCourseWare (OCW) platforms typically\ngenerate a list of recommendations in one of two ways, i.e. through the\ncontent-based filtering, or user-based collaborative filtering (CF). In this\npaper, the conceptual idea of the content recommendation module was provided,\nwhich is capable of proposing the related decks (presentations, educational\nmaterial, etc.) to the user having in mind past user activities, preferences,\ntype and content similarity, etc. It particularly analyses suitable techniques\nfor implementation of the user-based CF approach and user-related features that\nare relevant for the content evaluation. The proposed approach also envisages a\nhybrid recommendation system as a combination of user-based and content-based\napproaches in order to provide a holistic and efficient solution for content\nrecommendation. Finally, for evaluation and testing purposes, a designated\ncontent recommendation module was implemented as part of the SlideWiki\nauthoring OCW platform.\n	http://arxiv.org/abs/1902.10376v1
18	3	github	bluemapleman/NewsRecommendSystem	个性化新闻推荐系统，A news recommendation system involving collaborative filtering,content-based recommendation and hot news recommendation, can be adapted easily to be put into use in other circumstances.	https://github.com/bluemapleman/NewsRecommendSystem
19	3	blog	How to build a content-based rating predictor	\nHello!\nI want to build and evaluate a content-based recommender system. I am using the standard MovieLens dataset: http://grouplens.org/datasets/movielens/latest/\n\nI would like to know how can i build a content-based predictor for movie ratings (1-5 stars). I can extract movie profiles from features like genres/actors/tags etc. I didn't find much around for content-based prediction algorithms, the majority of results are for collaborative filtering and latent factor model approaches. Thus any advice on how i can proceed will be very appreciated!\n	https://www.reddit.com/r/datascience/comments/5az3op/how_to_build_a_contentbased_rating_predictor/
24	3	handbook	Stanford CS229 Machine Learning Notes	Lecture notes from Stanford's CS229 course by Andrew Ng.	https://cs229.stanford.edu/
\.


--
-- Data for Name: community_uploads; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.community_uploads (id, title, description, resource_type, status, user_id, url) FROM stdin;
4	test2	desc	Course	rejected	3	https://www.google.com/
1	FastAPI Course	A complete FastAPI tutorial	Course	approved	2	
2	FastAPI Course	A complete FastAPI tutorial	Course	rejected	2	https://fastapi.tiangolo.com/
5	Nice resource	very nice	Blog	approved	3	https://www.google.com/
6	Github test	test	GitHub	approved	3	https://www.google.com/
3	test	test	GitHub	rejected	3	https://www.google.com/
7	Course	new course	Course	approved	3	https://www.google.com/
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, email, hashed_password, is_admin) FROM stdin;
1	test@example.com	$2b$12$c2ZSaCdmOtjTNtOO504XSOILZHfN2VojYtjN2DnhHWiSE3EtQbFde	\N
3	sahil@email.com	$2b$12$4dTCwvoH2RPvQnvRSfnOhus5i4csm/Fq8PrRyHVPLXa4WokZRezGG	t
2	test1@example.com	$2b$12$vLmZ3LztDXqPazonaHJeL.wC572vjataAHBmEWhdrlLqcCvT3mwvO	t
\.


--
-- Name: bookmarks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bookmarks_id_seq', 24, true);


--
-- Name: community_uploads_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.community_uploads_id_seq', 7, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: bookmarks bookmarks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookmarks
    ADD CONSTRAINT bookmarks_pkey PRIMARY KEY (id);


--
-- Name: community_uploads community_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_uploads
    ADD CONSTRAINT community_uploads_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_bookmarks_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookmarks_id ON public.bookmarks USING btree (id);


--
-- Name: ix_bookmarks_url; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookmarks_url ON public.bookmarks USING btree (url);


--
-- Name: ix_community_uploads_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_community_uploads_id ON public.community_uploads USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: bookmarks bookmarks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookmarks
    ADD CONSTRAINT bookmarks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: community_uploads community_uploads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.community_uploads
    ADD CONSTRAINT community_uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

