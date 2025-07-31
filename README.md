# MyDramaList Unofficial API

A serverless FastAPI-based web scraper for MyDramaList.com, designed for deployment on Vercel.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FB1PL0B%2FMyDramaList-Unofficial-API)

> **Note**: This project is inspired from [@tbdsux/kuryana](https://github.com/tbdsux/kuryana). Special thanks to [@tbdsux](https://github.com/tbdsux)!

## 🚀 Features

- **Comprehensive API**: 9 endpoints covering drama search, details, cast, episodes, reviews, people, seasonal data, lists, and user drama lists
- **Serverless Architecture**: Optimized for Vercel deployment with cold start handling
- **Rate Limiting**: Built-in delays to respect MyDramaList.com's servers
- **Error Handling**: Consistent JSON error responses with proper HTTP status codes
- **Modular Design**: Separate scraping logic for maintainability

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search/q/{query}` | Search for dramas by query |
| GET | `/api/id/{slug}` | Get drama details by slug |
| GET | `/api/id/{slug}/cast` | Get cast information for a drama |
| GET | `/api/id/{slug}/episodes` | Get episode details for a drama |
| GET | `/api/id/{slug}/reviews` | Get reviews for a drama |
| GET | `/api/people/{people_id}` | Get person details by ID |
| GET | `/api/seasonal/{year}/{quarter}` | Get seasonal dramas (quarter: 1-4) |
| GET | `/api/list/{id}` | Get a specific drama list by ID |
| GET | `/api/dramalist/{user_id}` | Get a user's drama list by user ID |
| GET | `/api/health` | Health check endpoint |

## 🛠️ Tech Stack

- **Python 3.12**: Primary language
- **FastAPI**: Web framework
- **BeautifulSoup4**: HTML parsing
- **Requests**: HTTP client
- **Uvicorn**: ASGI server

## 📁 Project Structure

```
project_root/
├── main.py              # FastAPI application
├── scraper.py           # Scraping logic
├── requirements.txt     # Dependencies
├── vercel.json          # Vercel configuration
├── static/
│   └── index.html      # API documentation page
└── README.md           # This file
```

## 🔧 Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd mydramalist-scraper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run development server**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health

## 🚀 Vercel Deployment

### Prerequisites
- [Vercel CLI](https://vercel.com/cli) installed
- Vercel account

### Deployment Steps

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

4. **Follow the prompts**:
   - Set up and deploy: `Y`
   - Which scope: Select your account/team
   - Link to existing project: `N` (for new project)
   - Project name: Enter desired name
   - Directory: `./` (current directory)

### Alternative: GitHub Integration

1. Push your code to a GitHub repository
2. Connect your GitHub account to Vercel
3. Import the repository in Vercel dashboard
4. Deploy automatically on every push

## 📊 Response Examples

### Search Results
```json
{
  "results": [
    {
      "title": "Squid Game",
      "slug": "40257-round-six",
      "year": "2021",
      "image": "https://i.mydramalist.com/X6vkX_4s.jpg?v=1",
      "rating": "8.4",
      "url": "https://mydramalist.com/40257-round-six"
    },
    {
      "title": "Squid Game in Conversation",
      "slug": "795618-squid-game-in-conversation",
      "year": "2025",
      "image": "https://i.mydramalist.com/5vWpAe_4s.jpg?v=1",
      "rating": "8.0",
      "url": "https://mydramalist.com/795618-squid-game-in-conversation"
    },
    {
      "title": "Squid Game Season 3",
      "slug": "771707-squid-game-season-3",
      "year": "2025",
      "image": "https://i.mydramalist.com/g0Rbn1_4s.jpg?v=1",
      "rating": "7.5",
      "url": "https://mydramalist.com/771707-squid-game-season-3"
    },
    {
      "title": "Squid Game Season 2",
      "slug": "714529-squid-game-season-2",
      "year": "2024",
      "image": "https://i.mydramalist.com/3o7eqj_4s.jpg?v=1",
      "rating": "8.1",
      "url": "https://mydramalist.com/714529-squid-game-season-2"
    }
  ],
  "total": 20
}
```

### Error Response
```json
{
  "code": 404,
  "error": true,
  "description": "404 Not Found"
}
```

## ⚠️ Important Notes

### Rate Limiting
- Built-in 1-second delay between requests
- Respects MyDramaList.com's servers
- Prevents overwhelming the target site

### Vercel Limitations
- **Execution Time**: 10 seconds (free tier)
- **Function Size**: 15MB maximum
- **Cold Starts**: First request may be slower

### Legal Compliance
- For educational purposes only
- Respects robots.txt and terms of service
- Includes proper user-agent headers
- Implements reasonable rate limiting

## 🔍 Error Handling

The API handles various error scenarios:

- **400 Bad Request**: Invalid parameters or private resources
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server-side errors

All errors return consistent JSON responses with error codes and descriptions.

## 🛡️ Best Practices

1. **Respect Rate Limits**: Don't make rapid successive requests
2. **Handle Errors**: Always check response status codes
3. **Cache Responses**: Implement client-side caching when possible
4. **Monitor Usage**: Be aware of Vercel function invocation limits

## 📝 License

This project is for educational purposes only. Please respect MyDramaList.com's terms of service and use responsibly.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues or questions:
1. Check the API documentation at the root URL
2. Review error responses for debugging information
3. Check Vercel function logs for deployment issues

---

**Note**: This scraper is designed to be respectful of MyDramaList.com's resources. Please use it responsibly and in accordance with their terms of service.
