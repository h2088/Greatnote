import uuid
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notebook, Page, PageUserShare, ShareLink, TopicFolder
from .views import WebpageExtractor


class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='password123'
        )

    def test_register_success(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'newuser')

    def test_register_duplicate_username_returns_400(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'testuser',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password_returns_400(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser2',
            'password': 'abc',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password_returns_401(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_me_unauthenticated_returns_401(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotebookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')

    def test_list_returns_only_own_notebooks(self):
        Notebook.objects.create(user=self.other, title='Other Notebook')
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/notebooks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'My Notebook')

    def test_list_unauthenticated_returns_401(self):
        response = self.client.get('/api/notebooks/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_includes_page_count(self):
        Page.objects.create(notebook=self.notebook, title='P1')
        Page.objects.create(notebook=self.notebook, title='P2')
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/notebooks/')
        self.assertEqual(response.data[0]['page_count'], 2)

    def test_create_notebook(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/notebooks/', {'title': 'New Notebook'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Notebook.objects.filter(user=self.user, title='New Notebook').exists())

    def test_retrieve_own_notebook(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/notebooks/{self.notebook.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'My Notebook')

    def test_retrieve_other_users_notebook_returns_404(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f'/api/notebooks/{self.notebook.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_own_notebook(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f'/api/notebooks/{self.notebook.id}/', {'title': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.title, 'Updated')

    def test_update_other_users_notebook_returns_404(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.patch(f'/api/notebooks/{self.notebook.id}/', {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_notebook(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/notebooks/{self.notebook.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Notebook.objects.filter(id=self.notebook.id).exists())

    def test_delete_other_users_notebook_returns_404(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.delete(f'/api/notebooks/{self.notebook.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notebook_detail_includes_nested_pages(self):
        Page.objects.create(notebook=self.notebook, title='Page 1')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/notebooks/{self.notebook.id}/')
        self.assertEqual(len(response.data['pages']), 1)
        self.assertEqual(response.data['pages'][0]['title'], 'Page 1')


class PageTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')
        self.other_notebook = Notebook.objects.create(user=self.other, title='Other Notebook')
        self.page = Page.objects.create(notebook=self.notebook, title='Page 1')

    def test_list_pages_in_own_notebook(self):
        Page.objects.create(notebook=self.notebook, title='Page 2')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/notebooks/{self.notebook.id}/pages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_pages_in_other_notebook_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/notebooks/{self.other_notebook.id}/pages/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_page_assigns_sequential_order(self):
        Page.objects.create(notebook=self.notebook, title='Page 2', order=1)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/pages/', {'title': 'Page 3'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['order'], 2)

    def test_create_page_in_other_notebook_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.other_notebook.id}/pages/', {'title': 'Hack'}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_own_page(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Page 1')

    def test_retrieve_other_users_page_returns_404(self):
        other_page = Page.objects.create(notebook=self.other_notebook, title='Other')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/pages/{other_page.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_page_title_and_content(self):
        self.client.force_authenticate(user=self.user)
        content = {'type': 'doc', 'content': []}
        response = self.client.patch(
            f'/api/pages/{self.page.id}/',
            {'title': 'Updated', 'content': content},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.page.refresh_from_db()
        self.assertEqual(self.page.title, 'Updated')
        self.assertEqual(self.page.content, content)

    def test_update_other_users_page_returns_404(self):
        other_page = Page.objects.create(notebook=self.other_notebook, title='Other')
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f'/api/pages/{other_page.id}/', {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_page(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Page.objects.filter(id=self.page.id).exists())

    def test_delete_other_users_page_returns_404(self):
        other_page = Page.objects.create(notebook=self.other_notebook, title='Other')
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/pages/{other_page.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_page_content_defaults_to_empty_dict(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/pages/', {'title': 'Empty'}
        )
        self.assertEqual(response.data['content'], {})

    def test_share_token_is_null_by_default(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertIsNone(response.data['share_token'])


class TopicFolderTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')
        self.other_notebook = Notebook.objects.create(user=self.other, title='Other Notebook')
        self.folder = TopicFolder.objects.create(notebook=self.notebook, name='Research')
        self.page = Page.objects.create(notebook=self.notebook, title='Page 1')

    def test_create_topic_folder(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/topic-folders/', {
            'notebook': self.notebook.id,
            'name': 'Ideas',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TopicFolder.objects.filter(notebook=self.notebook, name='Ideas').exists())

    def test_list_topic_folders_filtered_by_notebook(self):
        TopicFolder.objects.create(notebook=self.notebook, name='Archive')
        TopicFolder.objects.create(notebook=self.other_notebook, name='Private')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/topic-folders/?notebook={self.notebook.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item['name'] for item in response.data}, {'Research', 'Archive'})

    def test_cannot_create_topic_folder_in_other_users_notebook(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/topic-folders/', {
            'notebook': self.other_notebook.id,
            'name': 'Hack',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_assign_page_to_topic_folder(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f'/api/pages/{self.page.id}/',
            {'topic_folder': self.folder.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.page.refresh_from_db()
        self.assertEqual(self.page.topic_folder_id, self.folder.id)

    def test_cannot_assign_page_to_folder_from_other_notebook(self):
        other_folder = TopicFolder.objects.create(notebook=self.other_notebook, name='Foreign')
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f'/api/pages/{self.page.id}/',
            {'topic_folder': other_folder.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_topic_folder_unassigns_existing_pages(self):
        self.page.topic_folder = self.folder
        self.page.save(update_fields=['topic_folder'])
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/topic-folders/{self.folder.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.page.refresh_from_db()
        self.assertIsNone(self.page.topic_folder)


class ImportWebpageTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')
        self.other_notebook = Notebook.objects.create(user=self.other, title='Other Notebook')
        self.folder = TopicFolder.objects.create(notebook=self.notebook, name='Web Clips')
        self.other_folder = TopicFolder.objects.create(notebook=self.other_notebook, name='Private')

    @patch('notebooks.views.fetch_webpage')
    def test_import_webpage_creates_page_with_remote_images(self, mock_fetch_webpage):
        doc = {
            'type': 'doc',
            'content': [
                {
                    'type': 'heading',
                    'attrs': {'level': 1},
                    'content': [{'type': 'text', 'text': 'Example article'}],
                },
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'Source: https://example.com/article'}],
                },
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'Import mode: Basic fallback (no readable text extracted)'}],
                },
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'Hello world'}],
                },
                {
                    'type': 'image',
                    'attrs': {'src': 'https://example.com/image.png', 'alt': 'hero', 'title': ''},
                },
            ],
        }
        parsed = MagicMock()
        parsed.title = 'Example article'
        parsed.base_url = 'https://example.com/article'
        parsed.get_plain_text.return_value = ''
        parsed.get_image_nodes.return_value = [doc['content'][1]]
        parsed.build_tiptap_doc.return_value = doc
        parsed.build_basic_tiptap_doc.return_value = doc
        mock_fetch_webpage.return_value = parsed
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/import-webpage/',
            {'url': 'https://example.com/article'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        page = Page.objects.get(id=response.data['id'])
        self.assertEqual(page.title, 'Example article')
        self.assertEqual(response.data['import_mode'], 'fallback')
        image_nodes = [node for node in page.content['content'] if node['type'] == 'image']
        self.assertEqual(len(image_nodes), 1)
        self.assertEqual(image_nodes[0]['attrs']['src'], 'https://example.com/image.png')

    def test_import_webpage_requires_url(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/import-webpage/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('notebooks.views.fetch_webpage')
    def test_import_webpage_can_assign_topic_folder(self, mock_fetch_webpage):
        parsed = MagicMock()
        parsed.title = 'Imported into folder'
        parsed.base_url = 'https://example.com/article'
        parsed.get_plain_text.return_value = ''
        parsed.get_image_nodes.return_value = []
        parsed.build_tiptap_doc.return_value = {'type': 'doc', 'content': []}
        parsed.build_basic_tiptap_doc.return_value = {'type': 'doc', 'content': []}
        mock_fetch_webpage.return_value = parsed
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/import-webpage/',
            {
                'url': 'https://example.com/article',
                'topic_folder': self.folder.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        page = Page.objects.get(id=response.data['id'])
        self.assertEqual(page.topic_folder_id, self.folder.id)
        self.assertEqual(response.data['import_mode'], 'fallback')

    @patch('notebooks.views.fetch_webpage')
    def test_import_webpage_rejects_folder_from_other_notebook(self, mock_fetch_webpage):
        parsed = MagicMock()
        parsed.title = 'Should not import'
        parsed.base_url = 'https://example.com/article'
        parsed.get_plain_text.return_value = ''
        parsed.get_image_nodes.return_value = []
        parsed.build_tiptap_doc.return_value = {'type': 'doc', 'content': []}
        parsed.build_basic_tiptap_doc.return_value = {'type': 'doc', 'content': []}
        mock_fetch_webpage.return_value = parsed
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/import-webpage/',
            {
                'url': 'https://example.com/article',
                'topic_folder': self.other_folder.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(OPENAI_API_KEY='test-key', OPENAI_MODEL='gpt-5.4')
    @patch('notebooks.views.OpenAI')
    @patch('notebooks.views.fetch_webpage')
    def test_import_webpage_uses_ai_to_structure_notes(self, mock_fetch_webpage, mock_openai_class):
        parsed = MagicMock()
        parsed.base_url = 'https://example.com/article'
        parsed.title = 'Raw article'
        parsed.get_plain_text.return_value = 'Paragraph one.\n\nParagraph two.'
        parsed.get_image_nodes.return_value = [
            {'type': 'image', 'attrs': {'src': 'https://example.com/image.png', 'alt': 'hero', 'title': ''}},
        ]
        parsed.build_basic_tiptap_doc.return_value = {'type': 'doc', 'content': [{'type': 'paragraph'}]}
        mock_fetch_webpage.return_value = parsed

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = '''
        {
          "title": "AI Notes Title",
          "summary": "A short summary.",
          "key_points": ["Point one", "Point two"],
          "body": ["Body paragraph one.", "Body paragraph two."]
        }
        '''
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/import-webpage/',
            {'url': 'https://example.com/article'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        page = Page.objects.get(id=response.data['id'])
        self.assertEqual(page.title, 'AI Notes Title')
        self.assertEqual(response.data['import_mode'], 'ai')
        self.assertEqual(response.data['import_detail'], 'gpt-5.4')
        content_texts = [
            node['content'][0]['text']
            for node in page.content['content']
            if node.get('content') and node['content'] and node['content'][0].get('type') == 'text'
        ]
        self.assertIn('Source: https://example.com/article', content_texts)
        self.assertIn('Import mode: AI organized (gpt-5.4)', content_texts)
        self.assertIn('Summary', content_texts)
        self.assertIn('A short summary.', content_texts)
        self.assertIn('Key Points', content_texts)
        self.assertIn('Notes', content_texts)
        self.assertIn('Body paragraph one.', content_texts)

    @override_settings(OPENAI_API_KEY='test-key', OPENAI_MODEL='gpt-5.4')
    @patch('notebooks.views.OpenAI')
    @patch('notebooks.views.fetch_webpage')
    def test_import_webpage_falls_back_to_basic_doc_when_ai_fails(self, mock_fetch_webpage, mock_openai_class):
        parsed = MagicMock()
        parsed.base_url = 'https://example.com/article'
        parsed.title = 'Fallback title'
        parsed.get_plain_text.return_value = 'Paragraph one.'
        parsed.get_image_nodes.return_value = []
        parsed.build_basic_tiptap_doc.return_value = {
            'type': 'doc',
            'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Source: https://example.com/article'}]}],
        }
        mock_fetch_webpage.return_value = parsed

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception('AI failed')

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/notebooks/{self.notebook.id}/import-webpage/',
            {'url': 'https://example.com/article'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        page = Page.objects.get(id=response.data['id'])
        self.assertEqual(page.title, 'Fallback title')
        self.assertEqual(response.data['import_mode'], 'fallback')
        self.assertIn('AI import failed', response.data['import_detail'])
        content_texts = [
            node['content'][0]['text']
            for node in page.content['content']
            if node.get('content') and node['content'] and node['content'][0].get('type') == 'text'
        ]
        self.assertIn('Source: https://example.com/article', content_texts)
        self.assertTrue(any(text.startswith('Import mode: Basic fallback') for text in content_texts))


class WebpageExtractorTests(TestCase):
    def test_prefers_article_content_and_ignores_nav_and_footer_text(self):
        extractor = WebpageExtractor('https://example.com/post')
        extractor.feed(
            '''
            <html>
              <head><title>Example Post</title></head>
              <body>
                <nav><p>Home</p><p>Pricing</p></nav>
                <article>
                  <h1>Main heading</h1>
                  <p>Important paragraph one.</p>
                  <p>Important paragraph two.</p>
                </article>
                <footer><p>Footer links</p></footer>
              </body>
            </html>
            '''
        )
        doc = extractor.build_tiptap_doc()
        texts = [
            node['content'][0]['text']
            for node in doc['content']
            if node.get('content')
        ]
        self.assertIn('Source: https://example.com/post', texts)
        self.assertIn('Main heading', texts)
        self.assertIn('Important paragraph one.', texts)
        self.assertIn('Important paragraph two.', texts)
        self.assertNotIn('Home', texts)
        self.assertNotIn('Pricing', texts)
        self.assertNotIn('Footer links', texts)

    def test_ignores_logo_images_outside_main_content(self):
        extractor = WebpageExtractor('https://example.com/post')
        extractor.feed(
            '''
            <html>
              <body>
                <img src="/logo.png" alt="logo" class="site-logo" />
                <p>Readable text.</p>
                <img src="/photo.jpg" alt="Article image" />
              </body>
            </html>
            '''
        )
        doc = extractor.build_tiptap_doc()
        image_nodes = [node for node in doc['content'] if node['type'] == 'image']
        self.assertEqual(len(image_nodes), 1)
        self.assertEqual(image_nodes[0]['attrs']['src'], 'https://example.com/photo.jpg')

    def test_extracts_douban_book_metadata_and_sections(self):
        extractor = WebpageExtractor('https://book.douban.com/subject/35603043/')
        html = '''
        <html>
          <head>
            <title>豆瓣图书</title>
            <meta name="description" content="一本关于民国司法史的著作" />
          </head>
          <body>
            <h1><span property="v:itemreviewed">施剑翘复仇案</span></h1>
            <div id="info">
              <span class="pl">作者</span>: 罗志田<br/>
              <span class="pl">出版社</span>: 广西师范大学出版社<br/>
              <span class="pl">ISBN</span>: 9787549565432<br/>
            </div>
            <strong property="v:average">8.7</strong>
            <span property="v:votes">1234</span>
            <h2><span>内容简介</span></h2>
            <div class="intro">
              <p>这是内容简介第一段。</p>
              <p>这是内容简介第二段。</p>
            </div>
            <h2><span>作者简介</span></h2>
            <div class="intro">
              <p>作者长期研究近代中国史。</p>
            </div>
          </body>
        </html>
        '''
        extractor.feed(html)
        extractor.close()
        extractor.enrich_from_html(html)

        plain_text = extractor.get_plain_text()
        self.assertEqual(extractor.title, '施剑翘复仇案')
        self.assertIn('作者 : 罗志田', plain_text)
        self.assertIn('出版社 : 广西师范大学出版社', plain_text)
        self.assertIn('ISBN : 9787549565432', plain_text)
        self.assertIn('Douban rating: 8.7 (1234 ratings)', plain_text)
        self.assertIn('内容简介', plain_text)
        self.assertIn('这是内容简介第一段。', plain_text)
        self.assertIn('作者简介', plain_text)
        self.assertIn('作者长期研究近代中国史。', plain_text)


class ShareLinkTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')
        self.page = Page.objects.create(notebook=self.notebook, title='My Page')

    def test_create_share_link(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/pages/{self.page.id}/share/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertTrue(ShareLink.objects.filter(page=self.page, is_active=True).exists())

    def test_create_share_link_is_idempotent(self):
        self.client.force_authenticate(user=self.user)
        r1 = self.client.post(f'/api/pages/{self.page.id}/share/')
        r2 = self.client.post(f'/api/pages/{self.page.id}/share/')
        self.assertEqual(r1.data['token'], r2.data['token'])
        self.assertEqual(ShareLink.objects.filter(page=self.page, is_active=True).count(), 1)

    def test_revoke_share_link(self):
        ShareLink.objects.create(page=self.page, is_active=True)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/pages/{self.page.id}/share/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShareLink.objects.filter(page=self.page, is_active=True).exists())

    def test_create_share_for_other_users_page_returns_404(self):
        other_notebook = Notebook.objects.create(user=self.other, title='Other')
        other_page = Page.objects.create(notebook=other_notebook, title='Other Page')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/pages/{other_page.id}/share/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_shared_page_returns_content(self):
        link = ShareLink.objects.create(page=self.page, is_active=True)
        response = self.client.get(f'/api/shared/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'My Page')
        self.assertEqual(response.data['notebook_title'], 'My Notebook')

    def test_public_shared_page_requires_no_auth(self):
        link = ShareLink.objects.create(page=self.page, is_active=True)
        response = self.client.get(f'/api/shared/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_share_link_returns_404(self):
        link = ShareLink.objects.create(page=self.page, is_active=False)
        response = self.client.get(f'/api/shared/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_share_token_returns_404(self):
        response = self.client.get(f'/api/shared/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_page_serializer_shows_active_share_token(self):
        link = ShareLink.objects.create(page=self.page, is_active=True)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.data['share_token'], str(link.token))

    def test_revoked_link_becomes_inaccessible(self):
        link = ShareLink.objects.create(page=self.page, is_active=True)
        self.client.force_authenticate(user=self.user)
        self.client.delete(f'/api/pages/{self.page.id}/share/')
        response = self.client.get(f'/api/shared/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_page_serializer_shows_null_share_token_after_revoke(self):
        ShareLink.objects.create(page=self.page, is_active=True)
        self.client.force_authenticate(user=self.user)
        self.client.delete(f'/api/pages/{self.page.id}/share/')
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertIsNone(response.data['share_token'])


class FavoritePageTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')
        self.other_notebook = Notebook.objects.create(user=self.other, title='Other Notebook')
        self.page = Page.objects.create(notebook=self.notebook, title='Page 1')
        self.fav_page = Page.objects.create(notebook=self.notebook, title='Fav Page', is_favorite=True)
        self.other_page = Page.objects.create(notebook=self.other_notebook, title='Other Fav', is_favorite=True)

    def test_favorite_page_toggle(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f'/api/pages/{self.page.id}/', {'is_favorite': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_favorite'])
        self.page.refresh_from_db()
        self.assertTrue(self.page.is_favorite)

    def test_unfavorite_page(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f'/api/pages/{self.fav_page.id}/', {'is_favorite': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_favorite'])
        self.fav_page.refresh_from_db()
        self.assertFalse(self.fav_page.is_favorite)

    def test_favorite_pages_list_returns_only_own_favorites(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/pages/favorites/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Fav Page')

    def test_favorite_pages_list_excludes_unfavorited(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/pages/favorites/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data]
        self.assertNotIn('Page 1', titles)

    def test_favorite_pages_list_unauthenticated_returns_401(self):
        response = self.client.get('/api/pages/favorites/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_see_other_users_favorites(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/pages/favorites/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data]
        self.assertNotIn('Other Fav', titles)

    def test_favorite_toggle_in_page_list_serializer(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/notebooks/{self.notebook.id}/')
        pages = response.data['pages']
        fav = next(p for p in pages if p['title'] == 'Fav Page')
        self.assertTrue(fav['is_favorite'])


class PageUserShareTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password123')
        self.shared_user = User.objects.create_user(username='shared', password='password123')
        self.other = User.objects.create_user(username='other', password='password123')
        self.notebook = Notebook.objects.create(user=self.owner, title='My Notebook')
        self.page = Page.objects.create(notebook=self.notebook, title='My Page')

    def test_share_page_with_specific_user(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/pages/{self.page.id}/share/users/',
            {'username': 'shared'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PageUserShare.objects.filter(page=self.page, user=self.shared_user).exists())

    def test_shared_user_can_read_page(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.shared_user)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'My Page')

    def test_shared_user_cannot_update_page(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.shared_user)
        response = self.client.patch(
            f'/api/pages/{self.page.id}/',
            {'title': 'Hacked'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.page.refresh_from_db()
        self.assertEqual(self.page.title, 'My Page')

    def test_shared_user_cannot_delete_page(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.shared_user)
        response = self.client.delete(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Page.objects.filter(id=self.page.id).exists())

    def test_non_shared_user_cannot_access_page(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoke_user_share(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            f'/api/pages/{self.page.id}/share/users/{self.shared_user.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PageUserShare.objects.filter(page=self.page, user=self.shared_user).exists())

    def test_revoked_user_loses_access(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.owner)
        self.client.delete(f'/api/pages/{self.page.id}/share/users/{self.shared_user.id}/')

        self.client.force_authenticate(user=self.shared_user)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_retains_full_access_after_sharing(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(
            f'/api/pages/{self.page.id}/',
            {'title': 'Updated'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(f'/api/pages/{self.page.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_share_with_nonexistent_user_returns_404(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/pages/{self.page.id}/share/users/',
            {'username': 'doesnotexist'}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_with_self_returns_400(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/pages/{self.page.id}/share/users/',
            {'username': 'owner'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_without_username_returns_400(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f'/api/pages/{self.page.id}/share/users/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_share_is_idempotent(self):
        self.client.force_authenticate(user=self.owner)
        r1 = self.client.post(
            f'/api/pages/{self.page.id}/share/users/',
            {'username': 'shared'}
        )
        r2 = self.client.post(
            f'/api/pages/{self.page.id}/share/users/',
            {'username': 'shared'}
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(PageUserShare.objects.filter(page=self.page, user=self.shared_user).count(), 1)

    def test_non_owner_cannot_share_page(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            f'/api/pages/{self.page.id}/share/users/',
            {'username': 'shared'}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_revoke_share(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.other)
        response = self.client.delete(
            f'/api/pages/{self.page.id}/share/users/{self.shared_user.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_shared_users(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/api/pages/{self.page.id}/share/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user']['username'], 'shared')

    def test_shared_with_me_returns_only_shared_pages(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)
        other_notebook = Notebook.objects.create(user=self.owner, title='Other')
        other_page = Page.objects.create(notebook=other_notebook, title='Other Page')
        # Do NOT share other_page

        self.client.force_authenticate(user=self.shared_user)
        response = self.client.get('/api/shared-with-me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'My Page')
        self.assertEqual(response.data[0]['owner'], 'owner')

    def test_shared_users_field_only_visible_to_owner(self):
        PageUserShare.objects.create(page=self.page, user=self.shared_user)

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(len(response.data['shared_users']), 1)

        self.client.force_authenticate(user=self.shared_user)
        response = self.client.get(f'/api/pages/{self.page.id}/')
        self.assertEqual(len(response.data['shared_users']), 0)

    def test_public_shared_page_still_works(self):
        link = ShareLink.objects.create(page=self.page, is_active=True)
        response = self.client.get(f'/api/shared/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'My Page')

    def test_revoked_public_link_returns_404(self):
        link = ShareLink.objects.create(page=self.page, is_active=True)
        self.client.force_authenticate(user=self.owner)
        self.client.delete(f'/api/pages/{self.page.id}/share/')
        response = self.client.get(f'/api/shared/{link.token}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AiEditTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='password123')
        self.other = User.objects.create_user(username='user2', password='password123')
        self.notebook = Notebook.objects.create(user=self.user, title='My Notebook')
        self.page = Page.objects.create(notebook=self.notebook, title='Page 1')

    @override_settings(OPENAI_API_KEY='test-key')
    @patch('notebooks.views.OpenAI')
    def test_ai_edit_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = '  Improved text  '
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'text': 'hello world', 'action': 'improve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Improved text')
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs['model'], 'gpt-5.4')
        self.assertEqual(call_kwargs['messages'][0]['role'], 'system')
        self.assertEqual(call_kwargs['messages'][1]['content'], 'hello world')

    @override_settings(OPENAI_API_KEY='test-key', OPENAI_MODEL='unsupported-model')
    @patch('notebooks.views.OpenAI')
    def test_ai_edit_falls_back_to_secondary_model(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = 'Recovered text'
        mock_client.chat.completions.create.side_effect = [
            Exception('model not found'),
            MagicMock(choices=[mock_choice]),
        ]

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'text': 'hello world', 'action': 'improve'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Recovered text')
        self.assertEqual(response.data['model'], 'gpt-5.4')
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        first_call = mock_client.chat.completions.create.call_args_list[0].kwargs
        second_call = mock_client.chat.completions.create.call_args_list[1].kwargs
        self.assertEqual(first_call['model'], 'unsupported-model')
        self.assertEqual(second_call['model'], 'gpt-5.4')

    def test_ai_edit_unauthenticated_returns_401(self):
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'text': 'hello', 'action': 'improve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ai_edit_other_users_page_returns_404(self):
        other_notebook = Notebook.objects.create(user=self.other, title='Other')
        other_page = Page.objects.create(notebook=other_notebook, title='Other Page')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{other_page.id}/ai-edit/',
            {'text': 'hello', 'action': 'improve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ai_edit_missing_text_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'action': 'improve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ai_edit_invalid_action_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'text': 'hello', 'action': 'invalid'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(OPENAI_API_KEY='')
    def test_ai_edit_no_api_key_returns_503(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'text': 'hello', 'action': 'improve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(OPENAI_API_KEY='test-key')
    @patch('notebooks.views.OpenAI')
    def test_ai_edit_openai_error_returns_502(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception('API Error')

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/pages/{self.page.id}/ai-edit/',
            {'text': 'hello', 'action': 'improve'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
