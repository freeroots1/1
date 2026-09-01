import express from 'express'
import Database from 'better-sqlite3'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'
import crypto from 'node:crypto'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(__dirname, '..')
const dataDir = process.env.DATA_DIR || path.join(rootDir, 'data')
fs.mkdirSync(dataDir, { recursive: true })

const db = new Database(path.join(dataDir, 'profit-calculator.db'))
db.pragma('journal_mode = WAL')
db.exec(`
  CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    school TEXT NOT NULL,
    name TEXT NOT NULL,
    startDate TEXT NOT NULL,
    endDate TEXT,
    location TEXT NOT NULL,
    days INTEGER NOT NULL DEFAULT 1,
    students INTEGER NOT NULL,
    price REAL NOT NULL,
    baseCost REAL NOT NULL DEFAULT 0,
    baseQuantity REAL NOT NULL DEFAULT 0,
    baseDays REAL NOT NULL DEFAULT 1,
    partTimeCost REAL NOT NULL DEFAULT 0,
    partTimeQuantity REAL NOT NULL DEFAULT 0,
    partTimeDays REAL NOT NULL DEFAULT 1,
    materialCost REAL NOT NULL DEFAULT 0,
    materialQuantity REAL NOT NULL DEFAULT 0,
    materialDays REAL NOT NULL DEFAULT 1,
    transportCost REAL NOT NULL DEFAULT 0,
    vehicleCount INTEGER NOT NULL DEFAULT 1,
    vehicleDays REAL NOT NULL DEFAULT 1,
    insuranceCost REAL NOT NULL DEFAULT 0,
    insuranceQuantity REAL NOT NULL DEFAULT 0,
    insuranceDays REAL NOT NULL DEFAULT 1,
    otherCost REAL NOT NULL DEFAULT 0,
    otherQuantity REAL NOT NULL DEFAULT 0,
    otherDays REAL NOT NULL DEFAULT 1,
    customCosts TEXT NOT NULL DEFAULT '[]',
    costModelVersion INTEGER NOT NULL DEFAULT 1,
    createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  )
`)

const existingColumns = new Set(db.prepare('PRAGMA table_info(projects)').all().map((column) => column.name))
if (!existingColumns.has('vehicleCount')) db.exec('ALTER TABLE projects ADD COLUMN vehicleCount INTEGER NOT NULL DEFAULT 1')
if (!existingColumns.has('costModelVersion')) db.exec('ALTER TABLE projects ADD COLUMN costModelVersion INTEGER NOT NULL DEFAULT 1')
if (!existingColumns.has('baseQuantity')) db.exec('ALTER TABLE projects ADD COLUMN baseQuantity REAL NOT NULL DEFAULT 0')
if (!existingColumns.has('partTimeQuantity')) db.exec('ALTER TABLE projects ADD COLUMN partTimeQuantity REAL NOT NULL DEFAULT 0')
if (!existingColumns.has('materialQuantity')) db.exec('ALTER TABLE projects ADD COLUMN materialQuantity REAL NOT NULL DEFAULT 0')
if (!existingColumns.has('insuranceQuantity')) db.exec('ALTER TABLE projects ADD COLUMN insuranceQuantity REAL NOT NULL DEFAULT 0')
if (!existingColumns.has('otherQuantity')) db.exec('ALTER TABLE projects ADD COLUMN otherQuantity REAL NOT NULL DEFAULT 0')
if (!existingColumns.has('baseDays')) db.exec('ALTER TABLE projects ADD COLUMN baseDays REAL NOT NULL DEFAULT 1')
if (!existingColumns.has('partTimeDays')) db.exec('ALTER TABLE projects ADD COLUMN partTimeDays REAL NOT NULL DEFAULT 1')
if (!existingColumns.has('materialDays')) db.exec('ALTER TABLE projects ADD COLUMN materialDays REAL NOT NULL DEFAULT 1')
if (!existingColumns.has('vehicleDays')) db.exec('ALTER TABLE projects ADD COLUMN vehicleDays REAL NOT NULL DEFAULT 1')
if (!existingColumns.has('insuranceDays')) db.exec('ALTER TABLE projects ADD COLUMN insuranceDays REAL NOT NULL DEFAULT 1')
if (!existingColumns.has('otherDays')) db.exec('ALTER TABLE projects ADD COLUMN otherDays REAL NOT NULL DEFAULT 1')
if (!existingColumns.has('customCosts')) db.exec("ALTER TABLE projects ADD COLUMN customCosts TEXT NOT NULL DEFAULT '[]'")

const seedProjects = [
  ['多日研学', '北京市第二中学', '西安历史文化研学营', '2026-05-20', '2026-05-24', '西安', 5, 180, 1280, 120000, 24000, 8640, 36000, 3600, 8160],
  ['多日研学', '上海市实验中学', '杭州西湖文化研学营', '2026-05-18', '2026-05-21', '杭州', 4, 150, 1200, 84000, 18000, 5400, 33000, 1800, 6000],
  ['多日研学', '广州市第十六中学', '红色文化研学之旅', '2026-05-15', '2026-05-18', '井冈山', 4, 120, 1360, 72000, 14400, 4320, 40800, 2160, 4800],
  ['多日研学', '成都市石室中学', '三星堆探秘研学营', '2026-05-12', '2026-05-15', '广汉', 4, 160, 1380, 96000, 19200, 7680, 34800, 2560, 7200],
  ['多日研学', '南京市金陵中学', '南京六朝文化研学营', '2026-05-10', '2026-05-13', '南京', 4, 140, 1240, 75600, 16800, 5600, 26600, 1960, 5040],
  ['单日研学', '苏州市第一中学', '园林建筑美学研学', '2026-05-08', '2026-05-08', '苏州', 1, 90, 460, 17600, 3600, 2700, 7200, 900, 1400],
]

if (db.prepare('SELECT COUNT(*) AS count FROM projects').get().count === 0) {
  const insert = db.prepare(`INSERT INTO projects (type, school, name, startDate, endDate, location, days, students, price, baseCost, partTimeCost, materialCost, transportCost, insuranceCost, otherCost) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
  const seed = db.transaction(() => seedProjects.forEach((project) => insert.run(...project)))
  seed()
}

// Compatibility migration: previous records stored cost totals. Convert the five per-student
// columns to unit prices, while retaining each project's total cost exactly. Transport keeps
// its prior total as a one-vehicle price because the historical vehicle count is unavailable.
db.prepare(`
  UPDATE projects SET
    baseCost = CASE WHEN students > 0 THEN baseCost / students ELSE baseCost END,
    partTimeCost = CASE WHEN students > 0 THEN partTimeCost / students ELSE partTimeCost END,
    materialCost = CASE WHEN students > 0 THEN materialCost / students ELSE materialCost END,
    insuranceCost = CASE WHEN students > 0 THEN insuranceCost / students ELSE insuranceCost END,
    otherCost = CASE WHEN students > 0 THEN otherCost / students ELSE otherCost END,
    vehicleCount = CASE WHEN vehicleCount > 0 THEN vehicleCount ELSE 1 END,
    costModelVersion = 2
  WHERE costModelVersion < 2
`).run()

// Version 3 gives every cost item its own quantity. Existing unit-price records use the
// student count as their initial quantity, which preserves every historical subtotal.
db.prepare(`
  UPDATE projects SET
    baseQuantity = students,
    partTimeQuantity = students,
    materialQuantity = students,
    insuranceQuantity = students,
    otherQuantity = students,
    costModelVersion = 3
  WHERE costModelVersion < 3
`).run()

// Version 4 adds an independent day count to every cost item. Historical items start
// at one day so their existing subtotals and the overall project cost remain unchanged.
db.prepare(`
  UPDATE projects SET
    baseDays = CASE WHEN baseDays > 0 THEN baseDays ELSE 1 END,
    partTimeDays = CASE WHEN partTimeDays > 0 THEN partTimeDays ELSE 1 END,
    materialDays = CASE WHEN materialDays > 0 THEN materialDays ELSE 1 END,
    vehicleDays = CASE WHEN vehicleDays > 0 THEN vehicleDays ELSE 1 END,
    insuranceDays = CASE WHEN insuranceDays > 0 THEN insuranceDays ELSE 1 END,
    otherDays = CASE WHEN otherDays > 0 THEN otherDays ELSE 1 END,
    costModelVersion = 4
  WHERE costModelVersion < 4
`).run()

const fields = ['type', 'school', 'name', 'startDate', 'endDate', 'location', 'days', 'students', 'price', 'baseCost', 'baseQuantity', 'baseDays', 'partTimeCost', 'partTimeQuantity', 'partTimeDays', 'materialCost', 'materialQuantity', 'materialDays', 'transportCost', 'vehicleCount', 'vehicleDays', 'insuranceCost', 'insuranceQuantity', 'insuranceDays', 'otherCost', 'otherQuantity', 'otherDays', 'customCosts']
const numericFields = new Set(['days', 'students', 'price', 'baseCost', 'baseQuantity', 'baseDays', 'partTimeCost', 'partTimeQuantity', 'partTimeDays', 'materialCost', 'materialQuantity', 'materialDays', 'transportCost', 'vehicleCount', 'vehicleDays', 'insuranceCost', 'insuranceQuantity', 'insuranceDays', 'otherCost', 'otherQuantity', 'otherDays'])

function normalizeCustomCosts(value) {
  let items = value
  if (typeof items === 'string') {
    try { items = JSON.parse(items) } catch { items = [] }
  }
  if (!Array.isArray(items)) return []
  return items.slice(0, 50).map((item, index) => {
    const numberValue = (field) => {
      const number = Number(item?.[field] || 0)
      return Number.isFinite(number) && number > 0 ? number : 0
    }
    return {
      id: String(item?.id || `custom-${index + 1}`).slice(0, 80),
      name: String(item?.name || '自定义成本').trim().slice(0, 40) || '自定义成本',
      price: numberValue('price'),
      quantity: numberValue('quantity'),
      days: numberValue('days'),
    }
  })
}

function deserializeProject(project) {
  return { ...project, customCosts: normalizeCustomCosts(project.customCosts) }
}

function normalizeProject(input) {
  const output = {}
  for (const field of fields) {
    if (field === 'customCosts') {
      output[field] = JSON.stringify(normalizeCustomCosts(input[field]))
    } else if (numericFields.has(field)) {
      const value = Number(input[field] || 0)
      output[field] = Number.isFinite(value) ? value : 0
    } else {
      output[field] = String(input[field] || '').trim()
    }
  }
  if (!output.type) output.type = '单日研学'
  if (!output.school || !output.name || !output.startDate || !output.location) throw new Error('请补充项目的必要信息')
  if (output.students <= 0 || output.price <= 0) throw new Error('学生人数和学生单价必须大于 0')
  if (output.days <= 0) output.days = 1
  for (const field of numericFields) if (output[field] < 0) output[field] = 0
  return output
}

const app = express()
app.use(express.json({ limit: '100kb' }))

app.get('/api/health', (_request, response) => response.json({ ok: true }))

const appUsername = process.env.APP_USERNAME || ''
const appPassword = process.env.APP_PASSWORD || ''

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(left)
  const rightBuffer = Buffer.from(right)
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer)
}

if (appUsername && appPassword) {
  app.use((request, response, next) => {
    const authorization = request.headers.authorization || ''
    if (authorization.startsWith('Basic ')) {
      try {
        const credentials = Buffer.from(authorization.slice(6), 'base64').toString('utf8')
        const separator = credentials.indexOf(':')
        const username = separator >= 0 ? credentials.slice(0, separator) : ''
        const password = separator >= 0 ? credentials.slice(separator + 1) : ''
        if (safeEqual(username, appUsername) && safeEqual(password, appPassword)) return next()
      } catch {
        // Invalid credentials fall through to the login challenge.
      }
    }
    response.set('WWW-Authenticate', 'Basic realm="研学利润测算", charset="UTF-8"')
    response.status(401).send('请输入研学利润测算访问账号和密码。')
  })
}

app.get('/api/projects', (_request, response) => {
  response.json(db.prepare('SELECT * FROM projects ORDER BY startDate DESC, id DESC').all().map(deserializeProject))
})
app.post('/api/projects', (request, response) => {
  try {
    const project = normalizeProject(request.body)
    const values = fields.map((field) => project[field])
    const result = db.prepare(`INSERT INTO projects (${fields.join(', ')}, costModelVersion) VALUES (${fields.map(() => '?').join(', ')}, 4)`).run(...values)
    response.status(201).json(deserializeProject(db.prepare('SELECT * FROM projects WHERE id = ?').get(result.lastInsertRowid)))
  } catch (error) { response.status(400).json({ error: error.message }) }
})
app.put('/api/projects/:id', (request, response) => {
  try {
    const project = normalizeProject(request.body)
    const values = fields.map((field) => project[field])
    const result = db.prepare(`UPDATE projects SET ${fields.map((field) => `${field} = ?`).join(', ')}, costModelVersion = 4, updatedAt = CURRENT_TIMESTAMP WHERE id = ?`).run(...values, request.params.id)
    if (!result.changes) return response.status(404).json({ error: '项目不存在或已删除' })
    response.json(deserializeProject(db.prepare('SELECT * FROM projects WHERE id = ?').get(request.params.id)))
  } catch (error) { response.status(400).json({ error: error.message }) }
})
app.delete('/api/projects/:id', (request, response) => {
  const result = db.prepare('DELETE FROM projects WHERE id = ?').run(request.params.id)
  if (!result.changes) return response.status(404).json({ error: '项目不存在或已删除' })
  response.status(204).end()
})

const distDir = path.join(rootDir, 'dist')
if (fs.existsSync(distDir)) {
  app.use(express.static(distDir))
  app.get('/{*splat}', (_request, response) => response.sendFile(path.join(distDir, 'index.html')))
}

const port = Number(process.env.PORT || 3000)
app.listen(port, '0.0.0.0', () => console.log(`研学利润测算服务已启动：http://0.0.0.0:${port}`))
