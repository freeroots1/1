import { useEffect, useMemo, useRef, useState } from 'react'
import {
  CalendarDays,
  ChevronRight,
  Compass,
  Download,
  Edit3,
  Plus,
  Printer,
  Search,
  Trash2,
  Users,
  X,
} from 'lucide-react'
import './App.css'

const emptyProject = {
  type: '单日研学',
  school: '',
  name: '',
  startDate: '',
  endDate: '',
  location: '',
  days: 1,
  students: '',
  price: '',
  baseCost: '',
  baseQuantity: '',
  baseDays: '',
  partTimeCost: '',
  partTimeQuantity: '',
  partTimeDays: '',
  materialCost: '',
  materialQuantity: '',
  materialDays: '',
  transportCost: '',
  vehicleCount: '',
  vehicleDays: '',
  insuranceCost: '',
  insuranceQuantity: '',
  insuranceDays: '',
  otherCost: '',
  otherQuantity: '',
  otherDays: '',
  customCosts: [],
}

const costItems = [
  { key: 'baseCost', quantityKey: 'baseQuantity', daysKey: 'baseDays', label: '基地成本', quantityUnit: '人' },
  { key: 'partTimeCost', quantityKey: 'partTimeQuantity', daysKey: 'partTimeDays', label: '兼职成本', quantityUnit: '人' },
  { key: 'materialCost', quantityKey: 'materialQuantity', daysKey: 'materialDays', label: '物料成本', quantityUnit: '人' },
  { key: 'transportCost', quantityKey: 'vehicleCount', daysKey: 'vehicleDays', label: '车辆成本', quantityUnit: '辆' },
  { key: 'insuranceCost', quantityKey: 'insuranceQuantity', daysKey: 'insuranceDays', label: '保险成本', quantityUnit: '人' },
  { key: 'otherCost', quantityKey: 'otherQuantity', daysKey: 'otherDays', label: '其他成本', quantityUnit: '人' },
]

const numericCostFields = costItems.flatMap(({ key, quantityKey, daysKey }) => [key, quantityKey, daysKey])
const projectsPerPage = 6

const formatCurrency = (value) => `${new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
}).format(Number(value || 0))} 元`

const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(Number(value || 0))

const formatDate = (project) => {
  if (!project.startDate) return '未填写'
  return project.endDate && project.endDate !== project.startDate
    ? `${project.startDate} ~ ${project.endDate}`
    : project.startDate
}

const calculationsFor = (project) => {
  const students = Number(project.students || 0)
  const revenue = students * Number(project.price || 0)
  const costDetails = Object.fromEntries(costItems.map(({ key, quantityKey, daysKey }) => [key, Number(project[key] || 0) * Number(project[quantityKey] || 0) * Number(project[daysKey] || 0)]))
  const customCosts = Array.isArray(project.customCosts) ? project.customCosts : []
  const customCostDetails = customCosts.map((item) => Number(item.price || 0) * Number(item.quantity || 0) * Number(item.days || 0))
  const cost = Object.values(costDetails).reduce((total, subtotal) => total + subtotal, 0) + customCostDetails.reduce((total, subtotal) => total + subtotal, 0)
  const profit = revenue - cost
  return { revenue, cost, profit, margin: revenue ? profit / revenue : 0, costDetails, customCostDetails }
}

const excelBorder = {
  top: { style: 'thin', color: { argb: 'FFD6D9DE' } },
  left: { style: 'thin', color: { argb: 'FFD6D9DE' } },
  bottom: { style: 'thin', color: { argb: 'FFD6D9DE' } },
  right: { style: 'thin', color: { argb: 'FFD6D9DE' } },
}

async function downloadProjectsExcel(projects) {
  const ExcelJSModule = await import('exceljs')
  const ExcelJS = ExcelJSModule.default ?? ExcelJSModule
  const workbook = new ExcelJS.Workbook()
  workbook.creator = '研学利润测算'
  workbook.created = new Date()
  workbook.calcProperties.fullCalcOnLoad = true
  workbook.calcProperties.forceFullCalc = true
  workbook.calcProperties.calcMode = 'auto'

  const rows = projects.map((project) => ({ project, summary: calculationsFor(project) }))
  const totalStudents = projects.reduce((sum, project) => sum + Number(project.students || 0), 0)
  const totalRevenue = rows.reduce((sum, row) => sum + row.summary.revenue, 0)
  const totalCost = rows.reduce((sum, row) => sum + row.summary.cost, 0)
  const totalProfit = totalRevenue - totalCost
  const exportDate = new Date().toLocaleDateString('zh-CN')

  const summarySheet = workbook.addWorksheet('项目汇总', {
    views: [{ state: 'frozen', ySplit: 5 }],
    pageSetup: { orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 0, paperSize: 9 },
  })
  summarySheet.columns = [
    { key: 'index', width: 7 }, { key: 'school', width: 22 }, { key: 'name', width: 28 },
    { key: 'type', width: 13 }, { key: 'date', width: 23 }, { key: 'students', width: 11 },
    { key: 'price', width: 14 }, { key: 'revenue', width: 16 }, { key: 'cost', width: 16 }, { key: 'profit', width: 16 }, { key: 'margin', width: 11 },
    { key: 'projectId', width: 2, hidden: true },
  ]
  summarySheet.mergeCells('A1:K1')
  summarySheet.getCell('A1').value = '研学项目利润汇总表'
  summarySheet.getCell('A1').font = { size: 20, bold: true, color: { argb: 'FF1F2329' } }
  summarySheet.getCell('A1').alignment = { horizontal: 'center', vertical: 'middle' }
  summarySheet.getRow(1).height = 36
  summarySheet.mergeCells('A2:K2')
  summarySheet.getCell('A2').value = `研学部门内部使用  |  导出日期：${exportDate}`
  summarySheet.getCell('A2').font = { size: 10, color: { argb: 'FF646A73' } }
  summarySheet.getCell('A2').alignment = { horizontal: 'center' }
  summarySheet.mergeCells('A3:K3')
  summarySheet.getCell('A3').value = `项目数量：${projects.length}    合作学校：${new Set(projects.map((project) => project.school)).size}    学生总人数：${formatNumber(totalStudents)}人    总收入：${formatCurrency(totalRevenue)}    总成本：${formatCurrency(totalCost)}    总利润：${formatCurrency(totalProfit)}`
  summarySheet.getCell('A3').font = { size: 11, bold: true, color: { argb: 'FF3370FF' } }
  summarySheet.getCell('A3').alignment = { horizontal: 'center', vertical: 'middle' }
  summarySheet.getCell('A3').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F6FF' } }
  summarySheet.getRow(3).height = 28

  const summaryHeaders = ['序号', '学校', '项目名称', '项目分类', '研学时间', '学生人数', '学生单价', '总收入', '总成本', '项目利润', '利润率']
  const headerRow = summarySheet.getRow(5)
  summaryHeaders.forEach((header, index) => { headerRow.getCell(index + 1).value = header })
  headerRow.height = 26
  headerRow.eachCell((cell) => {
    cell.font = { size: 10, bold: true, color: { argb: 'FF3F4650' } }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF3F5F7' } }
    cell.alignment = { horizontal: 'center', vertical: 'middle' }
    cell.border = excelBorder
  })

  rows.forEach(({ project, summary }, index) => {
    const row = summarySheet.addRow([index + 1, project.school, project.name, project.type, formatDate(project), Number(project.students), Number(project.price), summary.revenue, summary.cost, summary.profit, summary.margin, project.id])
    row.getCell(8).value = { formula: `F${row.number}*G${row.number}`, result: summary.revenue }
    row.getCell(9).value = { formula: `SUMIF('成本明细'!$J:$J,$L${row.number},'成本明细'!$I:$I)`, result: summary.cost }
    row.getCell(10).value = { formula: `H${row.number}-I${row.number}`, result: summary.profit }
    row.getCell(11).value = { formula: `IFERROR(J${row.number}/H${row.number},0)`, result: summary.margin }
    row.height = 24
    row.eachCell((cell, columnNumber) => {
      cell.font = { size: 10, color: { argb: 'FF1F2329' } }
      cell.alignment = { horizontal: [1, 4, 5, 6].includes(columnNumber) ? 'center' : columnNumber >= 7 ? 'right' : 'left', vertical: 'middle' }
      cell.border = excelBorder
    })
    ;[7, 8, 9, 10].forEach((columnNumber) => { row.getCell(columnNumber).numFmt = '#,##0" 元"' })
    row.getCell(11).numFmt = '0.0%'
  })

  const firstProjectRow = 6
  const lastProjectRow = firstProjectRow + rows.length - 1
  const totalRow = summarySheet.addRow(['', '合计', '', '', '', totalStudents, '', totalRevenue, totalCost, totalProfit, totalRevenue ? totalProfit / totalRevenue : 0])
  totalRow.getCell(6).value = { formula: `SUM(F${firstProjectRow}:F${lastProjectRow})`, result: totalStudents }
  totalRow.getCell(8).value = { formula: `SUM(H${firstProjectRow}:H${lastProjectRow})`, result: totalRevenue }
  totalRow.getCell(9).value = { formula: `SUM(I${firstProjectRow}:I${lastProjectRow})`, result: totalCost }
  totalRow.getCell(10).value = { formula: `SUM(J${firstProjectRow}:J${lastProjectRow})`, result: totalProfit }
  totalRow.getCell(11).value = { formula: `IFERROR(J${totalRow.number}/H${totalRow.number},0)`, result: totalRevenue ? totalProfit / totalRevenue : 0 }
  summarySheet.mergeCells(totalRow.number, 2, totalRow.number, 5)
  totalRow.height = 26
  totalRow.eachCell((cell, columnNumber) => {
    cell.font = { size: 10, bold: true, color: { argb: 'FF1F2329' } }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF1F6FF' } }
    cell.alignment = { horizontal: columnNumber >= 6 ? 'right' : 'center', vertical: 'middle' }
    cell.border = excelBorder
  })
  ;[8, 9, 10].forEach((columnNumber) => { totalRow.getCell(columnNumber).numFmt = '#,##0" 元"' })
  totalRow.getCell(11).numFmt = '0.0%'
  summarySheet.autoFilter = `A5:K${totalRow.number - 1}`
  summarySheet.pageSetup.printArea = `A1:K${totalRow.number}`
  summarySheet.pageSetup.printTitlesRow = '5:5'

  const detailSheet = workbook.addWorksheet('成本明细', {
    views: [{ state: 'frozen', ySplit: 4 }],
    pageSetup: { orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 0, paperSize: 9 },
  })
  detailSheet.columns = [
    { width: 7 }, { width: 20 }, { width: 25 }, { width: 18 }, { width: 14 },
    { width: 12 }, { width: 9 }, { width: 10 }, { width: 16 }, { width: 2, hidden: true },
  ]
  detailSheet.mergeCells('A1:I1')
  detailSheet.getCell('A1').value = '研学项目成本明细表'
  detailSheet.getCell('A1').font = { size: 19, bold: true }
  detailSheet.getCell('A1').alignment = { horizontal: 'center' }
  detailSheet.getRow(1).height = 34
  detailSheet.mergeCells('A2:I2')
  detailSheet.getCell('A2').value = `研学部门内部使用  |  导出日期：${exportDate}`
  detailSheet.getCell('A2').font = { size: 10, color: { argb: 'FF646A73' } }
  detailSheet.getCell('A2').alignment = { horizontal: 'center' }
  const detailHeaders = ['序号', '学校', '项目名称', '成本项目', '单价', '数量', '单位', '天数', '小计']
  const detailHeaderRow = detailSheet.getRow(4)
  detailHeaders.forEach((header, index) => { detailHeaderRow.getCell(index + 1).value = header })
  detailHeaderRow.height = 26
  detailHeaderRow.eachCell((cell) => {
    cell.font = { size: 10, bold: true }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF3F5F7' } }
    cell.alignment = { horizontal: 'center', vertical: 'middle' }
    cell.border = excelBorder
  })

  let detailIndex = 1
  projects.forEach((project) => {
    const summary = calculationsFor(project)
    const details = [
      ...costItems.map(({ key, quantityKey, daysKey, label, quantityUnit }) => ({ label, price: Number(project[key] || 0), quantity: Number(project[quantityKey] || 0), unit: quantityUnit, days: Number(project[daysKey] || 0), subtotal: summary.costDetails[key] })),
      ...(Array.isArray(project.customCosts) ? project.customCosts : []).map((item, index) => ({ label: item.name || '自定义成本', price: Number(item.price || 0), quantity: Number(item.quantity || 0), unit: '', days: Number(item.days || 0), subtotal: summary.customCostDetails[index] })),
    ]
    details.forEach((item) => {
      const row = detailSheet.addRow([detailIndex, project.school, project.name, item.label, item.price, item.quantity, item.unit, item.days, item.subtotal, project.id])
      row.getCell(9).value = { formula: `E${row.number}*F${row.number}*H${row.number}`, result: item.subtotal }
      row.height = 23
      row.eachCell((cell, columnNumber) => {
        cell.font = { size: 10 }
        cell.alignment = { horizontal: columnNumber >= 5 ? 'right' : columnNumber === 1 ? 'center' : 'left', vertical: 'middle' }
        cell.border = excelBorder
      })
      row.getCell(5).numFmt = '#,##0" 元"'
      row.getCell(9).numFmt = '#,##0" 元"'
      detailIndex += 1
    })
  })
  detailSheet.autoFilter = `A4:I${detailSheet.rowCount}`
  detailSheet.pageSetup.printArea = `A1:I${detailSheet.rowCount}`
  detailSheet.pageSetup.printTitlesRow = '4:4'

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `研学项目利润汇总_${new Date().toISOString().slice(0, 10)}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function Brand({ compact = false }) {
  return (
    <div className="brand" aria-label="研学利润测算">
      <span className="brand-mark"><Compass size={compact ? 18 : 21} strokeWidth={2.25} /></span>
      <span>研学利润测算</span>
    </div>
  )
}

function StatGrid({ stats }) {
  const items = [
    ['项目数量', stats.projectCount, 'default'],
    ['合作学校', stats.schoolCount, 'default'],
    ['学生总人数', stats.studentCount, 'default'],
    ['总收入', formatCurrency(stats.totalRevenue), 'default'],
    ['总成本', formatCurrency(stats.totalCost), 'default'],
    ['总利润', formatCurrency(stats.totalProfit), 'accent'],
    ['平均利润率', `${(stats.averageMargin * 100).toFixed(1)}%`, 'accent'],
  ]

  return (
    <section className="stat-grid" aria-label="统计数据">
      {items.map(([label, value, tone]) => (
        <div className="stat-item" key={label}>
          <span>{label}</span>
          <strong className={tone}>{value}</strong>
        </div>
      ))}
    </section>
  )
}

function ProjectTable({ projects, onEdit, onDelete, onPrint, compact = false, emptyMessage = '暂无项目' }) {
  if (compact) {
    if (!projects.length) return <div className="mobile-empty-state">{emptyMessage}</div>
    return (
      <div className="project-cards">
        {projects.map((project) => {
          const { profit } = calculationsFor(project)
          return (
            <button className="project-card" key={project.id} onClick={() => onEdit(project)}>
              <div className="project-card-main">
                <strong>{project.school}</strong>
                <span>{project.name}</span>
                <small><CalendarDays size={14} /> {formatDate(project)}</small>
                <small><span className="project-type-badge">{project.type || '未分类'}</span> <i /> <Users size={14} /> {formatNumber(project.students)}人</small>
              </div>
              <div className="project-card-profit">
                <small>利润</small>
                <strong>{formatCurrency(profit)}</strong>
              </div>
              <ChevronRight size={19} />
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <div className="table-scroll">
      <table className="project-table">
        <colgroup>
          <col className="col-school" />
          <col className="col-project" />
          <col className="col-date" />
          <col className="col-type" />
          <col className="col-students" />
          <col className="col-price" />
          <col className="col-money" />
          <col className="col-money" />
          <col className="col-money" />
          <col className="col-actions" />
        </colgroup>
        <thead>
          <tr>
            <th>学校</th>
            <th>项目名称</th>
            <th>研学时间</th>
            <th>项目分类</th>
            <th>学生人数</th>
            <th>学生单价</th>
            <th>总收入</th>
            <th>总成本</th>
            <th>项目利润</th>
            <th aria-label="操作" />
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => {
            const { revenue, cost, profit } = calculationsFor(project)
            return (
              <tr key={project.id}>
                <td className="school-name" title={project.school}>{project.school}</td>
                <td className="project-name" title={project.name}>{project.name}</td>
                <td className="date-cell" title={formatDate(project)}>{formatDate(project)}</td>
                <td><span className="project-type-badge">{project.type || '未分类'}</span></td>
                <td>{formatNumber(project.students)}</td>
                <td>{formatCurrency(project.price)}</td>
                <td className="currency-blue">{formatCurrency(revenue)}</td>
                <td>{formatCurrency(cost)}</td>
                <td className="currency-blue">{formatCurrency(profit)}</td>
                <td className="actions-cell">
                  <div className="row-actions">
                    <button aria-label={`编辑 ${project.name}`} title="编辑" onClick={() => onEdit(project)}><Edit3 size={18} /></button>
                    <button className="print-row-button" aria-label={`打印 ${project.name}`} title="打印" onClick={() => onPrint(project)}><Printer size={16} /><span>打印</span></button>
                    <button aria-label={`删除 ${project.name}`} title="删除" className="danger" onClick={() => onDelete(project)}><Trash2 size={18} /></button>
                  </div>
                </td>
              </tr>
            )
          })}
          {!projects.length && <tr><td className="empty-table-cell" colSpan="10">{emptyMessage}</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

function ProjectSearch({ value, onChange, inputRef }) {
  return (
    <label className="project-search">
      <Search size={17} />
      <input ref={inputRef} value={value} onChange={(event) => onChange(event.target.value)} placeholder="搜索学校、项目、单日、多日…" aria-label="搜索项目" />
      {value && <button type="button" onClick={() => onChange('')} aria-label="清空搜索"><X size={15} /></button>}
    </label>
  )
}

function ProjectPagination({ currentPage, totalPages, resultCount, onPageChange }) {
  return (
    <footer className="project-pagination">
      <span>共 {resultCount} 个项目，每页 {projectsPerPage} 个</span>
      <nav aria-label="项目分页">
        <button type="button" onClick={() => onPageChange(currentPage - 1)} disabled={currentPage <= 1} aria-label="上一页">上一页</button>
        <strong>第 {currentPage} / {totalPages} 页</strong>
        <button type="button" onClick={() => onPageChange(currentPage + 1)} disabled={currentPage >= totalPages} aria-label="下一页">下一页</button>
      </nav>
    </footer>
  )
}

function ProjectPanel({ title, projects, onEdit, onDelete, onPrint, onShowAll, showAll, searchTerm, onSearchChange, searchInputRef, currentPage, totalPages, resultCount, onPageChange }) {
  return (
    <section className="project-panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {!showAll && <button className="text-button" onClick={onShowAll}>查看全部 <ChevronRight size={17} /></button>}
        {showAll && <ProjectSearch value={searchTerm} onChange={onSearchChange} inputRef={searchInputRef} />}
      </div>
      <ProjectTable projects={projects} onEdit={onEdit} onDelete={onDelete} onPrint={onPrint} emptyMessage={searchTerm ? '没有找到符合条件的项目' : '暂无项目'} />
      {showAll && <ProjectPagination currentPage={currentPage} totalPages={totalPages} resultCount={resultCount} onPageChange={onPageChange} />}
    </section>
  )
}

function NumberInput({ value, onChange, suffix = '元', placeholder = '请输入金额', min = 0 }) {
  return (
    <div className="number-input">
      <input type="number" min={min} value={value} placeholder={placeholder} onChange={onChange} />
      <span>{suffix}</span>
    </div>
  )
}

function ProjectModal({ project, onClose, onSave, onPrint }) {
  const isEditing = Boolean(project?.id)
  const [form, setForm] = useState(project ? { ...project, customCosts: Array.isArray(project.customCosts) ? project.customCosts : [] } : { ...emptyProject, customCosts: [] })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const summary = calculationsFor(form)

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const addCustomCost = () => setForm((current) => ({
    ...current,
    customCosts: [...current.customCosts, { id: `custom-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, name: '', price: '', quantity: '', days: '' }],
  }))
  const updateCustomCost = (index, key, value) => setForm((current) => ({
    ...current,
    customCosts: current.customCosts.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item),
  }))
  const removeCustomCost = (index) => setForm((current) => ({
    ...current,
    customCosts: current.customCosts.filter((_, itemIndex) => itemIndex !== index),
  }))

  const submit = async (event) => {
    event.preventDefault()
    if (!form.school.trim() || !form.name.trim() || !form.startDate || !form.location.trim() || !Number(form.students) || !Number(form.price)) {
      setError('请补充学校、项目、时间、地点、学生人数和学生单价。')
      return
    }
    setSaving(true)
    setError('')
    try {
      await onSave({
        ...form,
        days: Number(form.days),
        students: Number(form.students),
        price: Number(form.price),
        ...Object.fromEntries(numericCostFields.map((key) => [key, Number(form[key] || 0)])),
        customCosts: form.customCosts.map((item) => ({ ...item, name: item.name.trim() || '自定义成本', price: Number(item.price || 0), quantity: Number(item.quantity || 0), days: Number(item.days || 0) })),
      })
      onClose()
    } catch (saveError) {
      setError(saveError.message || '保存失败，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="project-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="modal-header">
          <h2 id="modal-title">{isEditing ? '编辑研学项目' : '新建研学项目'}</h2>
          <button className="icon-close" onClick={onClose} aria-label="关闭"><X size={21} /></button>
        </header>
        <form onSubmit={submit}>
          <div className="form-section">
            <h3>项目信息</h3>
            <div className="form-grid two-column">
              <label className="field">
                <span>项目类型</span>
                <div className="type-switch" role="group" aria-label="项目类型">
                  {['单日研学', '多日研学'].map((type) => <button type="button" onClick={() => update('type', type)} className={form.type === type ? 'selected' : ''} key={type}>{type}</button>)}
                </div>
              </label>
              <label className="field">
                <span>学校名称 <b>*</b></span>
                <input value={form.school} placeholder="请输入学校名称" onChange={(event) => update('school', event.target.value)} />
              </label>
              <label className="field">
                <span>项目名称 <b>*</b></span>
                <input value={form.name} placeholder="请输入项目名称" onChange={(event) => update('name', event.target.value)} />
              </label>
              <div className="field">
                <span>研学时间 <b>*</b></span>
                <div className="date-inputs">
                  <input type="date" value={form.startDate} onChange={(event) => update('startDate', event.target.value)} onInput={(event) => update('startDate', event.currentTarget.value)} />
                  <span>至</span>
                  <input type="date" value={form.endDate} min={form.startDate} onChange={(event) => update('endDate', event.target.value)} onInput={(event) => update('endDate', event.currentTarget.value)} />
                </div>
              </div>
              <label className="field">
                <span>研学地点 <b>*</b></span>
                <input value={form.location} placeholder="请输入研学地点" onChange={(event) => update('location', event.target.value)} />
              </label>
              <label className="field">
                <span>天数</span>
                <NumberInput value={form.days} suffix="天" placeholder="请输入天数" min={1} onChange={(event) => update('days', event.target.value)} />
              </label>
            </div>
          </div>
          <div className="form-section revenue-section">
            <h3>收入</h3>
            <div className="form-grid two-column">
              <label className="field">
                <span>学生人数 <b>*</b></span>
                <NumberInput value={form.students} suffix="人" placeholder="请输入学生人数" onChange={(event) => update('students', event.target.value)} />
              </label>
              <label className="field">
                <span>学生单价 <b>*</b></span>
                <NumberInput value={form.price} onChange={(event) => update('price', event.target.value)} />
              </label>
            </div>
            <div className="calculation-hint">预计收入 <strong>{formatCurrency(summary.revenue)}</strong></div>
          </div>
          <div className="form-section">
            <h3>成本</h3>
            <div className="cost-table" aria-label="成本明细">
              <div className="cost-table-head" aria-hidden="true">
                <span>成本项目</span><span>单价</span><span>数量</span><span>天数</span><span>小计</span><span />
              </div>
              {costItems.map(({ key, quantityKey, daysKey, label, quantityUnit }) => (
                <div className="cost-row" key={key}>
                  <strong className="cost-name">{label}</strong>
                  <label className="cost-control">
                    <span>单价</span>
                    <NumberInput value={form[key]} suffix="元" placeholder="单价" onChange={(event) => update(key, event.target.value)} />
                  </label>
                  <span className="multiply-sign">×</span>
                  <label className="cost-control">
                    <span>数量</span>
                    <NumberInput value={form[quantityKey]} suffix={quantityUnit} placeholder="数量" onChange={(event) => update(quantityKey, event.target.value)} />
                  </label>
                  <span className="multiply-sign">×</span>
                  <label className="cost-control">
                    <span>天数</span>
                    <NumberInput value={form[daysKey]} suffix="天" placeholder="天数" onChange={(event) => update(daysKey, event.target.value)} />
                  </label>
                  <div className="cost-subtotal"><span>小计</span><strong>{formatCurrency(summary.costDetails[key])}</strong></div>
                  <span className="cost-action-space" />
                </div>
              ))}
              {form.customCosts.map((item, index) => (
                <div className="cost-row custom-cost-row" key={item.id}>
                  <input className="custom-cost-name" value={item.name} aria-label={`自定义成本 ${index + 1} 名称`} placeholder="成本名称" onChange={(event) => updateCustomCost(index, 'name', event.target.value)} />
                  <label className="cost-control">
                    <span>单价</span>
                    <NumberInput value={item.price} suffix="元" placeholder="单价" onChange={(event) => updateCustomCost(index, 'price', event.target.value)} />
                  </label>
                  <span className="multiply-sign">×</span>
                  <label className="cost-control">
                    <span>数量</span>
                    <NumberInput value={item.quantity} suffix="" placeholder="数量" onChange={(event) => updateCustomCost(index, 'quantity', event.target.value)} />
                  </label>
                  <span className="multiply-sign">×</span>
                  <label className="cost-control">
                    <span>天数</span>
                    <NumberInput value={item.days} suffix="天" placeholder="天数" onChange={(event) => updateCustomCost(index, 'days', event.target.value)} />
                  </label>
                  <div className="cost-subtotal"><span>小计</span><strong>{formatCurrency(summary.customCostDetails[index])}</strong></div>
                  <button type="button" className="remove-cost-button" aria-label={`删除自定义成本 ${index + 1}`} title="删除此项" onClick={() => removeCustomCost(index)}><Trash2 size={16} /></button>
                </div>
              ))}
              <div className="add-cost-row"><button type="button" onClick={addCustomCost}><Plus size={15} /> 添加自定义成本</button></div>
              <div className="cost-total-row"><span>成本合计</span><strong>{formatCurrency(summary.cost)}</strong></div>
            </div>
          </div>
          <div className="summary-strip">
            <div><span>总成本</span><strong>{formatCurrency(summary.cost)}</strong></div>
            <div><span>项目利润</span><strong>{formatCurrency(summary.profit)}</strong></div>
            <div><span>利润率</span><strong>{(summary.margin * 100).toFixed(1)}%</strong></div>
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <footer className="modal-footer">
            {isEditing && <button type="button" className="button secondary modal-print-button" onClick={() => onPrint(form)}><Printer size={17} />打印预览</button>}
            <button type="button" className="button secondary" onClick={onClose}>取消</button>
            <button className="button primary" type="submit" disabled={saving}>{saving ? '保存中…' : '保存项目'}</button>
          </footer>
        </form>
      </section>
    </div>
  )
}

function ProjectPrintPreview({ project, onClose }) {
  const summary = calculationsFor(project)
  const customCosts = Array.isArray(project.customCosts) ? project.customCosts : []
  const printCosts = [
    ...costItems.map(({ key, quantityKey, daysKey, label, quantityUnit }) => ({
      label,
      price: Number(project[key] || 0),
      quantity: Number(project[quantityKey] || 0),
      quantityUnit,
      days: Number(project[daysKey] || 0),
      subtotal: summary.costDetails[key],
    })),
    ...customCosts.map((item, index) => ({
      label: item.name || '自定义成本',
      price: Number(item.price || 0),
      quantity: Number(item.quantity || 0),
      quantityUnit: '',
      days: Number(item.days || 0),
      subtotal: summary.customCostDetails[index],
    })),
  ]

  return (
    <div className="print-preview-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="print-preview" role="dialog" aria-modal="true" aria-labelledby="print-preview-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="print-preview-toolbar">
          <button type="button" className="button secondary" onClick={onClose}>返回</button>
          <button type="button" className="button primary" onClick={() => window.print()}><Printer size={17} />打印</button>
        </div>
        <article className="print-sheet">
          <header className="print-title">
            <div>
              <p>研学部门内部使用</p>
              <h2 id="print-preview-title">研学项目利润测算表</h2>
            </div>
            <span>打印日期：{new Date().toLocaleDateString('zh-CN')}</span>
          </header>

          <section className="print-info-grid" aria-label="项目信息">
            <div><span>项目分类</span><strong>{project.type || '未分类'}</strong></div>
            <div><span>学校名称</span><strong>{project.school}</strong></div>
            <div><span>项目名称</span><strong>{project.name}</strong></div>
            <div><span>研学时间</span><strong>{formatDate(project)}</strong></div>
            <div><span>研学地点</span><strong>{project.location || '未填写'}</strong></div>
            <div><span>研学天数</span><strong>{formatNumber(project.days)}天</strong></div>
          </section>

          <section className="print-revenue">
            <div><span>学生人数</span><strong>{formatNumber(project.students)}人</strong></div>
            <div><span>学生单价</span><strong>{formatCurrency(project.price)}</strong></div>
            <div><span>总收入</span><strong>{formatCurrency(summary.revenue)}</strong></div>
          </section>

          <section className="print-cost-section">
            <h3>成本明细</h3>
            <table className="print-cost-table">
              <thead><tr><th>成本项目</th><th>单价</th><th>数量</th><th>天数</th><th>小计</th></tr></thead>
              <tbody>
                {printCosts.map((item, index) => (
                  <tr key={`${item.label}-${index}`}>
                    <td>{item.label}</td>
                    <td>{formatCurrency(item.price)}</td>
                    <td>{formatNumber(item.quantity)}{item.quantityUnit}</td>
                    <td>{formatNumber(item.days)}天</td>
                    <td>{formatCurrency(item.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr><td colSpan="4">成本合计</td><td>{formatCurrency(summary.cost)}</td></tr></tfoot>
            </table>
          </section>

          <section className="print-summary" aria-label="利润汇总">
            <div><span>总收入</span><strong>{formatCurrency(summary.revenue)}</strong></div>
            <div><span>总成本</span><strong>{formatCurrency(summary.cost)}</strong></div>
            <div><span>项目利润</span><strong>{formatCurrency(summary.profit)}</strong></div>
            <div><span>利润率</span><strong>{(summary.margin * 100).toFixed(1)}%</strong></div>
          </section>

          <footer className="print-signatures"><span>经办人：________________</span><span>复核人：________________</span></footer>
        </article>
      </section>
    </div>
  )
}

function AllProjectsPrintPreview({ projects, onClose, onDownloadExcel, isDownloadingExcel }) {
  const rows = projects.map((project) => ({ project, summary: calculationsFor(project) }))
  const totalStudents = projects.reduce((sum, project) => sum + Number(project.students || 0), 0)
  const totalRevenue = rows.reduce((sum, row) => sum + row.summary.revenue, 0)
  const totalCost = rows.reduce((sum, row) => sum + row.summary.cost, 0)
  const totalProfit = totalRevenue - totalCost

  return (
    <div className="print-preview-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="print-preview all-projects-preview" role="dialog" aria-modal="true" aria-labelledby="all-projects-print-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="print-preview-toolbar">
          <button type="button" className="button secondary" onClick={onClose}>返回</button>
          <button type="button" className="button secondary excel-download-button" onClick={onDownloadExcel} disabled={isDownloadingExcel}><Download size={17} />{isDownloadingExcel ? '生成中…' : '下载 Excel'}</button>
          <button type="button" className="button primary" onClick={() => window.print()}><Printer size={17} />打印全部</button>
        </div>
        <article className="print-sheet all-projects-print-sheet">
          <header className="print-title">
            <div>
              <p>研学部门内部使用</p>
              <h2 id="all-projects-print-title">研学项目利润汇总表</h2>
            </div>
            <span>打印日期：{new Date().toLocaleDateString('zh-CN')}</span>
          </header>

          <section className="all-projects-summary" aria-label="全部项目统计">
            <div><span>项目数量</span><strong>{projects.length}</strong></div>
            <div><span>合作学校</span><strong>{new Set(projects.map((project) => project.school)).size}</strong></div>
            <div><span>学生总人数</span><strong>{formatNumber(totalStudents)}人</strong></div>
            <div><span>总收入</span><strong>{formatCurrency(totalRevenue)}</strong></div>
            <div><span>总成本</span><strong>{formatCurrency(totalCost)}</strong></div>
            <div><span>总利润</span><strong>{formatCurrency(totalProfit)}</strong></div>
          </section>

          <section className="all-projects-table-section">
            <table className="print-cost-table all-projects-print-table">
              <colgroup><col className="print-col-index" /><col className="print-col-school" /><col className="print-col-name" /><col className="print-col-type" /><col className="print-col-date" /><col className="print-col-students" /><col className="print-col-money" /><col className="print-col-money" /><col className="print-col-money" /><col className="print-col-money" /><col className="print-col-margin" /></colgroup>
              <thead><tr><th>序号</th><th>学校</th><th>项目名称</th><th>项目分类</th><th>研学时间</th><th>学生人数</th><th>学生单价</th><th>总收入</th><th>总成本</th><th>项目利润</th><th>利润率</th></tr></thead>
              <tbody>
                {rows.map(({ project, summary }, index) => (
                  <tr key={project.id}>
                    <td>{index + 1}</td>
                    <td>{project.school}</td>
                    <td>{project.name}</td>
                    <td>{project.type}</td>
                    <td>{formatDate(project)}</td>
                    <td>{formatNumber(project.students)}</td>
                    <td>{formatCurrency(project.price)}</td>
                    <td>{formatCurrency(summary.revenue)}</td>
                    <td>{formatCurrency(summary.cost)}</td>
                    <td>{formatCurrency(summary.profit)}</td>
                    <td>{(summary.margin * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr><td colSpan="5">合计</td><td>{formatNumber(totalStudents)}</td><td>-</td><td>{formatCurrency(totalRevenue)}</td><td>{formatCurrency(totalCost)}</td><td>{formatCurrency(totalProfit)}</td><td>{totalRevenue ? `${(totalProfit / totalRevenue * 100).toFixed(1)}%` : '0.0%'}</td></tr></tfoot>
            </table>
          </section>
          <footer className="print-signatures"><span>经办人：________________</span><span>复核人：________________</span></footer>
        </article>
      </section>
    </div>
  )
}

function MobileHeader() {
  return (
    <header className="mobile-header">
      <Brand compact />
    </header>
  )
}

function App() {
  const [projects, setProjects] = useState([])
  const [editingProject, setEditingProject] = useState(null)
  const [printingProject, setPrintingProject] = useState(null)
  const [isPrintingAll, setPrintingAll] = useState(false)
  const [isDownloadingExcel, setDownloadingExcel] = useState(false)
  const [isModalOpen, setModalOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const desktopSearchRef = useRef(null)
  const mobileSearchRef = useRef(null)

  const loadProjects = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/projects')
      if (!response.ok) throw new Error('无法读取项目数据')
      setProjects(await response.json())
      setError('')
    } catch {
      setError('无法连接数据服务。请确认服务已启动。')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProjects() }, [])

  const stats = useMemo(() => {
    const calculated = projects.map(calculationsFor)
    const totalRevenue = calculated.reduce((sum, item) => sum + item.revenue, 0)
    const totalCost = calculated.reduce((sum, item) => sum + item.cost, 0)
    return {
      projectCount: projects.length,
      schoolCount: new Set(projects.map((project) => project.school)).size,
      studentCount: projects.reduce((sum, project) => sum + Number(project.students || 0), 0),
      totalRevenue,
      totalCost,
      totalProfit: totalRevenue - totalCost,
      averageMargin: totalRevenue ? (totalRevenue - totalCost) / totalRevenue : 0,
    }
  }, [projects])

  const openCreate = () => { setEditingProject(null); setModalOpen(true) }
  const openEdit = (project) => { setEditingProject(project); setModalOpen(true) }
  const handleDownloadExcel = async () => {
    setDownloadingExcel(true)
    try {
      await downloadProjectsExcel(projects)
    } catch (downloadError) {
      console.error('Excel 文件生成失败', downloadError)
      window.alert(downloadError.message || 'Excel 文件生成失败，请稍后重试。')
    } finally {
      setDownloadingExcel(false)
    }
  }
  const saveProject = async (data) => {
    const method = data.id ? 'PUT' : 'POST'
    const endpoint = data.id ? `/api/projects/${data.id}` : '/api/projects'
    const response = await fetch(endpoint, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
    if (!response.ok) {
      const result = await response.json().catch(() => ({}))
      throw new Error(result.error || '保存失败')
    }
    await loadProjects()
  }
  const deleteProject = async (project) => {
    if (!window.confirm(`确定删除「${project.name}」吗？`)) return
    const response = await fetch(`/api/projects/${project.id}`, { method: 'DELETE' })
    if (!response.ok) { window.alert('删除失败，请稍后重试。'); return }
    await loadProjects()
  }
  const changeSearch = (value) => { setSearchTerm(value); setCurrentPage(1) }
  const filteredProjects = useMemo(() => {
    const keyword = searchTerm.trim().toLocaleLowerCase('zh-CN')
    if (!keyword) return projects
    return projects.filter((project) => [project.school, project.name, project.type, project.location, project.startDate, project.endDate]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase('zh-CN')
      .includes(keyword))
  }, [projects, searchTerm])
  const totalPages = Math.max(1, Math.ceil(filteredProjects.length / projectsPerPage))
  const visiblePage = Math.min(currentPage, totalPages)
  const paginatedProjects = filteredProjects.slice((visiblePage - 1) * projectsPerPage, visiblePage * projectsPerPage)
  const shownProjects = paginatedProjects

  return (
    <div className="app-shell notranslate" translate="no">
      <div className="mobile-only"><MobileHeader /></div>
      <main className="app-main">
        <header className="page-header">
          <div>
            <h1>项目管理</h1>
            <p>项目统计、利润测算与项目管理</p>
          </div>
          <div className="page-actions">
            <button className="button secondary excel-download-button" onClick={handleDownloadExcel} disabled={!projects.length || isDownloadingExcel}><Download size={17} />{isDownloadingExcel ? '生成中…' : '下载 Excel'}</button>
            <button className="button secondary print-all-button" onClick={() => setPrintingAll(true)} disabled={!projects.length}><Printer size={17} />打印全部</button>
            <button className="button primary create-button" onClick={openCreate}><Plus size={19} /> <span className="desktop-create">新建项目</span><span className="mobile-create">新建</span></button>
          </div>
        </header>
        {loading ? <div className="state-message">正在加载项目数据…</div> : error ? <div className="state-message error-state"><span>{error}</span><button className="text-button" onClick={loadProjects}>重新连接</button></div> : (
          <>
            <StatGrid stats={stats} />
            <ProjectPanel
              title="全部项目"
              projects={shownProjects}
              onEdit={openEdit}
              onDelete={deleteProject}
              onPrint={setPrintingProject}
              showAll
              searchTerm={searchTerm}
              onSearchChange={changeSearch}
              searchInputRef={desktopSearchRef}
              currentPage={visiblePage}
              totalPages={totalPages}
              resultCount={filteredProjects.length}
              onPageChange={setCurrentPage}
            />
            <section className="mobile-project-section">
              <div className="mobile-project-heading">
                <h2>全部项目</h2>
                <ProjectSearch value={searchTerm} onChange={changeSearch} inputRef={mobileSearchRef} />
              </div>
              <ProjectTable compact projects={shownProjects} onEdit={openEdit} onDelete={deleteProject} emptyMessage={searchTerm ? '没有找到符合条件的项目' : '暂无项目'} />
              <ProjectPagination currentPage={visiblePage} totalPages={totalPages} resultCount={filteredProjects.length} onPageChange={setCurrentPage} />
            </section>
          </>
        )}
      </main>
      {isModalOpen && <ProjectModal project={editingProject} onClose={() => setModalOpen(false)} onSave={saveProject} onPrint={setPrintingProject} />}
      {printingProject && <ProjectPrintPreview project={printingProject} onClose={() => setPrintingProject(null)} />}
      {isPrintingAll && <AllProjectsPrintPreview projects={projects} onClose={() => setPrintingAll(false)} onDownloadExcel={handleDownloadExcel} isDownloadingExcel={isDownloadingExcel} />}
    </div>
  )
}

export default App
