(function(root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.YaochengDispatchAdvisor = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';

  var DEFAULT_BUS_TYPES = [59, 55, 53, 48, 45, 37, 19];

  function number(value) {
    var parsed = parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function intValue(value) {
    return Math.max(0, Math.floor(number(value)));
  }

  function distribute(total, parts) {
    var count = Math.max(0, Math.floor(parts));
    if (!count) return [];
    var whole = Math.floor(Math.max(0, total) / count);
    var extra = Math.max(0, total) % count;
    var result = [];
    for (var i = 0; i < count; i += 1) result.push(whole + (i < extra ? 1 : 0));
    return result;
  }

  function effectiveSeats(seats, reserveSeats) {
    return Math.max(0, intValue(seats) - intValue(reserveSeats));
  }

  function splitAllowed(value, fallback) {
    if (value === undefined || value === null || String(value).trim() === '') return fallback !== false;
    return !/^(0|false|no|n|否|不允许|禁止)$/i.test(String(value).trim());
  }

  function normalizeSplitRule(value, legacyAllowSplit) {
    if (value === true) return 'allow';
    if (value === false) return 'forbid';
    var normalized = String(value == null ? '' : value).trim().toLowerCase();
    if (/^(forbid|never|0|false|no|n|否|不允许|禁止|禁止拆班)$/.test(normalized)) return 'forbid';
    if (/^(allow|yes|1|true|y|是|允许|可拆|允许拆班)$/.test(normalized)) return 'allow';
    if (/^(follow|default|跟随|跟随整体|按整体策略)$/.test(normalized)) return 'follow';
    if (legacyAllowSplit === false) return 'forbid';
    if (legacyAllowSplit === true) return 'allow';
    return 'follow';
  }

  function recognizedSplitRule(value) {
    var normalized = String(value == null ? '' : value).trim().toLowerCase();
    if (!normalized) return true;
    return /^(forbid|never|0|false|no|n|否|不允许|禁止|禁止拆班|allow|yes|1|true|y|是|允许|可拆|允许拆班|follow|default|跟随|跟随整体|按整体策略)$/.test(normalized);
  }

  function normalizeClasses(rows) {
    if (!Array.isArray(rows)) return [];
    return rows.map(function(row, index) {
      var rule = normalizeSplitRule(row && row.splitRule, row && row.allowSplit);
      return {
        id: row && row.id !== undefined ? row.id : index + 1,
        name: String(row && row.name || '').trim() || ('第' + (index + 1) + '班'),
        students: intValue(row && row.students),
        teachers: intValue(row && row.teachers),
        splitRule: rule,
        allowSplit: rule !== 'forbid',
        note: String(row && row.note || '').trim()
      };
    }).filter(function(item) {
      return item.students + item.teachers > 0;
    });
  }

  function compactHeader(value) {
    return String(value == null ? '' : value).replace(/[\s_\-（）()]/g, '').toLowerCase();
  }

  function parseClassRows(rows) {
    var source = Array.isArray(rows) ? rows : [];
    var aliases = {
      sequence: ['序号', '编号', 'no', 'number'],
      name: ['班级', '班级名称', '班名'],
      students: ['学生', '学生数', '学生人数', '人数'],
      teachers: ['教师', '教师数', '教师人数', '老师', '老师人数', '随班教师', '随班教师人数'],
      split: ['允许拆班', '是否允许拆班', '可拆班', '拆班规则'],
      note: ['备注', '说明']
    };
    var normalizedAliases = {};
    Object.keys(aliases).forEach(function(key) {
      normalizedAliases[key] = aliases[key].map(compactHeader);
    });
    var firstDataIndex = source.findIndex(function(row) {
      return Array.isArray(row) && row.some(function(cell) { return String(cell == null ? '' : cell).trim(); });
    });
    if (firstDataIndex < 0) return { classes: [], errors: ['表格中没有可导入的班级数据。'] };
    var firstRow = source[firstDataIndex].map(compactHeader);
    var indexes = {};
    Object.keys(normalizedAliases).forEach(function(key) {
      indexes[key] = firstRow.findIndex(function(cell) { return normalizedAliases[key].indexOf(cell) >= 0; });
    });
    var hasHeader = indexes.name >= 0 && indexes.students >= 0;
    var recognizedHeaderCount = Object.keys(indexes).filter(function(key) { return indexes[key] >= 0; }).length;
    if (!hasHeader && recognizedHeaderCount > 0) {
      var missingHeaders = [];
      if (indexes.name < 0) missingHeaders.push('班级名称');
      if (indexes.students < 0) missingHeaders.push('学生人数');
      return { classes: [], errors: ['Excel缺少必填列：' + missingHeaders.join('、') + '。请使用曜程班级导入模板。'] };
    }
    var start = hasHeader ? firstDataIndex + 1 : firstDataIndex;
    var classes = [];
    var errors = [];
    var names = {};
    for (var i = start; i < source.length; i += 1) {
      var row = Array.isArray(source[i]) ? source[i] : [];
      if (!row.some(function(cell) { return String(cell == null ? '' : cell).trim(); })) continue;
      var offset = !hasHeader && /^\d+$/.test(String(row[0] == null ? '' : row[0]).trim()) && row.length >= 3 ? 1 : 0;
      var nameRaw = hasHeader ? row[indexes.name] : row[offset];
      var studentsRaw = hasHeader ? row[indexes.students] : row[offset + 1];
      var teachersRaw = hasHeader && indexes.teachers >= 0 ? row[indexes.teachers] : row[offset + 2];
      var splitRaw = hasHeader && indexes.split >= 0 ? row[indexes.split] : row[offset + 3];
      var noteRaw = hasHeader && indexes.note >= 0 ? row[indexes.note] : row[offset + 4];
      var name = String(nameRaw == null ? '' : nameRaw).trim();
      var students = Number(studentsRaw);
      var teachers = teachersRaw === undefined || String(teachersRaw).trim() === '' ? 0 : Number(teachersRaw);
      var rowNumber = i + 1;
      if (!name) {
        errors.push('第' + rowNumber + '行缺少班级名称。');
        continue;
      }
      if (!Number.isFinite(students) || students <= 0 || Math.floor(students) !== students) {
        errors.push('第' + rowNumber + '行“' + name + '”的学生人数必须是正整数。');
        continue;
      }
      if (!Number.isFinite(teachers) || teachers < 0 || Math.floor(teachers) !== teachers) {
        errors.push('第' + rowNumber + '行“' + name + '”的随班教师人数必须是非负整数。');
        continue;
      }
      if (!recognizedSplitRule(splitRaw)) {
        errors.push('第' + rowNumber + '行“' + name + '”的拆班规则无法识别，请填写“跟随”、“禁止”或“允许”。');
        continue;
      }
      var nameKey = name.toLowerCase();
      if (names[nameKey]) {
        errors.push('第' + rowNumber + '行班级名称“' + name + '”重复。');
        continue;
      }
      names[nameKey] = true;
      if (classes.length >= 200) {
        errors.push('一次最多导入200个班级，请拆分项目后再导入。');
        break;
      }
      var rule = normalizeSplitRule(splitRaw);
      classes.push({
        id: classes.length + 1,
        name: name,
        students: students,
        teachers: teachers,
        splitRule: rule,
        allowSplit: rule !== 'forbid',
        note: String(noteRaw == null ? '' : noteRaw).trim()
      });
    }
    if (!classes.length && !errors.length) errors.push('表格中没有可导入的班级数据。');
    return { classes: classes, errors: errors };
  }

  function buildClasses(input) {
    var imported = normalizeClasses(input.classes);
    if (imported.length) return imported;
    var classCount = intValue(input.classCount);
    var students = distribute(intValue(input.studentCount), classCount);
    var teachers = distribute(intValue(input.teacherCount), classCount);
    return students.map(function(count, index) {
      return {
        id: index + 1,
        name: '第' + (index + 1) + '班',
        students: count,
        teachers: teachers[index] || 0,
        splitRule: 'follow',
        allowSplit: true,
        note: ''
      };
    }).filter(function(item) {
      return item.students + item.teachers > 0;
    });
  }

  function normalizeFleet(rows, fallbackTypes) {
    var source = Array.isArray(rows) && rows.length
      ? rows
      : (fallbackTypes || DEFAULT_BUS_TYPES).map(function(seats) { return { seats: seats, enabled: true, count: null }; });
    var bySeats = {};
    source.forEach(function(row) {
      var entry = typeof row === 'number' ? { seats: row } : (row || {});
      var seats = intValue(entry.seats);
      if (entry.enabled === false || seats < 7 || seats > 80) return;
      var countRaw = entry.count;
      var count = countRaw === undefined || countRaw === null || String(countRaw).trim() === '' || intValue(countRaw) === 0
        ? null
        : intValue(countRaw);
      if (!bySeats[seats]) bySeats[seats] = { seats: seats, count: count };
      else if (bySeats[seats].count === null || count === null) bySeats[seats].count = null;
      else bySeats[seats].count += count;
    });
    return Object.keys(bySeats).map(function(key) { return bySeats[key]; }).sort(function(a, b) { return b.seats - a.seats; });
  }

  function planFitsFleet(plan, options) {
    var fleet = normalizeFleet(options.availableFleet, options.busTypes || DEFAULT_BUS_TYPES);
    var used = {};
    plan.forEach(function(seats) { used[seats] = (used[seats] || 0) + 1; });
    return Object.keys(used).every(function(key) {
      var entry = fleet.find(function(item) { return item.seats === intValue(key); });
      return !!entry && (entry.count === null || used[key] <= entry.count);
    });
  }

  function recommendOnceDetailed(people, options) {
    var reserveSeats = intValue(options.reserveSeats);
    var available = normalizeFleet(options.availableFleet, options.busTypes || DEFAULT_BUS_TYPES).map(function(item) {
      return { seats: item.seats, remaining: item.count };
    });
    var plan = [];
    var remaining = intValue(people);
    while (remaining > 0) {
      var choices = available.filter(function(item) { return item.remaining === null || item.remaining > 0; });
      if (!choices.length) break;
      choices.sort(function(a, b) { return a.seats - b.seats; });
      var selected = choices.find(function(item) { return effectiveSeats(item.seats, reserveSeats) >= remaining; });
      if (!selected) selected = choices[choices.length - 1];
      plan.push(selected.seats);
      remaining -= effectiveSeats(selected.seats, reserveSeats);
      if (selected.remaining !== null) selected.remaining -= 1;
      if (plan.length > 80) break;
    }
    return { plan: plan, remaining: Math.max(0, remaining) };
  }

  function recommendOnce(people, options) {
    return recommendOnceDetailed(people, options).plan;
  }

  function recommendBusesDetailed(basePeople, responsibleStaff, options) {
    var details = recommendOnceDetailed(basePeople, options);
    var plan = details.plan;
    for (var i = 0; i < 8; i += 1) {
      var required = intValue(basePeople) + Math.max(0, intValue(responsibleStaff) - plan.length);
      var capacity = plan.reduce(function(sum, seats) { return sum + effectiveSeats(seats, options.reserveSeats); }, 0);
      if (capacity >= required) return { plan: plan, remaining: 0 };
      details = recommendOnceDetailed(required, options);
      plan = details.plan;
      if (details.remaining > 0) return details;
    }
    return { plan: plan, remaining: Math.max(0, intValue(basePeople) - plan.reduce(function(sum, seats) { return sum + effectiveSeats(seats, options.reserveSeats); }, 0)) };
  }

  function recommendBuses(basePeople, responsibleStaff, options) {
    return recommendBusesDetailed(basePeople, responsibleStaff, options).plan;
  }

  function canPackWholeClasses(classes, plan, reserveSeats) {
    var remaining = plan.map(function(seats) { return effectiveSeats(seats, reserveSeats); });
    var sorted = classes.slice().sort(function(a, b) {
      return (b.students + b.teachers) - (a.students + a.teachers);
    });
    for (var i = 0; i < sorted.length; i += 1) {
      var count = sorted[i].students + sorted[i].teachers;
      var target = -1;
      var bestSpace = Infinity;
      for (var j = 0; j < remaining.length; j += 1) {
        if (remaining[j] >= count && remaining[j] - count < bestSpace) {
          target = j;
          bestSpace = remaining[j] - count;
        }
      }
      if (target < 0) return false;
      remaining[target] -= count;
    }
    return true;
  }

  function improveWholeClassPlan(plan, classes, options) {
    if (!classes.length || canPackWholeClasses(classes, plan, options.reserveSeats)) return plan;
    var types = normalizeFleet(options.availableFleet, options.busTypes || DEFAULT_BUS_TYPES).map(function(item) { return item.seats; }).sort(function(a, b) { return a - b; });
    if (!types.length) return plan;
    var maxEffective = effectiveSeats(types[types.length - 1], options.reserveSeats);
    if (classes.some(function(item) { return item.students + item.teachers > maxEffective; })) return plan;
    var current = plan.slice();
    for (var round = 0; round <= classes.length; round += 1) {
      var candidates = [];
      for (var i = 0; i < current.length; i += 1) {
        for (var j = 0; j < types.length; j += 1) {
          if (types[j] <= current[i]) continue;
          var upgraded = current.slice();
          upgraded[i] = types[j];
          if (planFitsFleet(upgraded, options) && canPackWholeClasses(classes, upgraded, options.reserveSeats)) candidates.push(upgraded);
        }
      }
      for (var typeIndex = 0; typeIndex < types.length; typeIndex += 1) {
        var expanded = current.concat(types[typeIndex]);
        if (planFitsFleet(expanded, options) && canPackWholeClasses(classes, expanded, options.reserveSeats)) candidates.push(expanded);
      }
      if (candidates.length) {
        candidates.sort(function(a, b) {
          var capacityA = a.reduce(function(sum, seats) { return sum + effectiveSeats(seats, options.reserveSeats); }, 0);
          var capacityB = b.reduce(function(sum, seats) { return sum + effectiveSeats(seats, options.reserveSeats); }, 0);
          return capacityA - capacityB || a.length - b.length;
        });
        return candidates[0].sort(function(a, b) { return b - a; });
      }
      var added = false;
      for (var addIndex = types.length - 1; addIndex >= 0; addIndex -= 1) {
        if (planFitsFleet(current.concat(types[addIndex]), options)) {
          current.push(types[addIndex]);
          added = true;
          break;
        }
      }
      if (!added) break;
    }
    return current;
  }

  function allocateClassAcrossBuses(cls, buses, allowSplit) {
    var total = cls.students + cls.teachers;
    var whole = buses
      .filter(function(bus) { return bus.effective - bus.used >= total; })
      .sort(function(a, b) { return (a.effective - a.used) - (b.effective - b.used); })[0];
    if (whole) {
      whole.items.push({ type: 'class', classId: cls.id, name: cls.name, students: cls.students, teachers: cls.teachers, splitRule: cls.splitRule, partial: false });
      whole.used += total;
      return true;
    }
    if (!allowSplit) return false;
    var remainingStudents = cls.students;
    var remainingTeachers = cls.teachers;
    var targets = buses
      .filter(function(bus) { return bus.effective - bus.used > 0; })
      .sort(function(a, b) { return (b.effective - b.used) - (a.effective - a.used); });
    for (var i = 0; i < targets.length && (remainingStudents + remainingTeachers) > 0; i += 1) {
      var bus = targets[i];
      var available = bus.effective - bus.used;
      if (available <= 0) continue;
      var teachers = remainingTeachers > 0 ? 1 : 0;
      var students = Math.min(remainingStudents, Math.max(0, available - teachers));
      if (students === 0 && remainingTeachers > 0 && available > 0) teachers = Math.min(remainingTeachers, available);
      if (students + teachers <= 0) continue;
      bus.items.push({ type: 'class', classId: cls.id, name: cls.name, students: students, teachers: teachers, splitRule: cls.splitRule, partial: true });
      bus.used += students + teachers;
      remainingStudents -= students;
      remainingTeachers -= teachers;
    }
    return remainingStudents + remainingTeachers <= 0;
  }

  function markPartialClasses(buses) {
    var groups = {};
    buses.forEach(function(bus) {
      bus.items.forEach(function(item) {
        if (item.type !== 'class') return;
        if (!groups[item.classId]) groups[item.classId] = [];
        groups[item.classId].push(item);
      });
    });
    Object.keys(groups).forEach(function(key) {
      var partial = groups[key].length > 1;
      groups[key].forEach(function(item) { item.partial = partial; });
    });
  }

  function balanceClassAllocations(buses, classes) {
    var byId = {};
    classes.forEach(function(item) { byId[item.id] = item; });
    for (var round = 0; round < 5000; round += 1) {
      var ordered = buses.slice().sort(function(a, b) { return a.used - b.used || a.num - b.num; });
      var target = null;
      var source = null;
      var movable = null;
      for (var sourceIndex = ordered.length - 1; sourceIndex > 0 && !movable; sourceIndex -= 1) {
        for (var targetIndex = 0; targetIndex < sourceIndex && !movable; targetIndex += 1) {
          var candidateSource = ordered[sourceIndex];
          var candidateTarget = ordered[targetIndex];
          if (candidateSource.used - candidateTarget.used <= 3 || candidateTarget.used >= candidateTarget.effective) continue;
          var candidateItem = candidateSource.items.find(function(item) {
            var cls = item.type === 'class' ? byId[item.classId] : null;
            if (!cls || cls.splitRule === 'forbid' || item.students <= 1) return false;
            var occupied = buses.filter(function(bus) {
              return bus.items.some(function(other) { return other.type === 'class' && other.classId === item.classId; });
            });
            return occupied.length < 2 || candidateTarget.items.some(function(other) { return other.type === 'class' && other.classId === item.classId; });
          });
          if (candidateItem) {
            source = candidateSource;
            target = candidateTarget;
            movable = candidateItem;
          }
        }
      }
      if (!movable) break;
      var targetItem = target.items.find(function(item) { return item.type === 'class' && item.classId === movable.classId; });
      var createTarget = !targetItem;
      if (!targetItem) {
        targetItem = {
          type: 'class',
          classId: movable.classId,
          name: movable.name,
          students: 0,
          teachers: 0,
          splitRule: movable.splitRule,
          partial: true
        };
        target.items.push(targetItem);
      }
      var moveTeacher = createTarget && targetItem.teachers === 0 && movable.teachers > 1 && target.used < target.effective;
      var maxPeopleMove = Math.max(1, Math.floor((source.used - target.used) / 2));
      var desiredStudents = Math.max(1, maxPeopleMove - (moveTeacher ? 1 : 0));
      if (createTarget && maxPeopleMove >= 5) desiredStudents = Math.max(desiredStudents, moveTeacher ? 4 : 5);
      var moveStudents = Math.min(movable.students - 1, target.effective - target.used - (moveTeacher ? 1 : 0), desiredStudents);
      if (moveStudents <= 0) break;
      movable.students -= moveStudents;
      targetItem.students += moveStudents;
      source.used -= moveStudents;
      target.used += moveStudents;
      if (moveTeacher) {
        movable.teachers -= 1;
        targetItem.teachers += 1;
        source.used -= 1;
        target.used += 1;
      }
    }
    markPartialClasses(buses);
  }

  function distributeExtra(name, count, buses) {
    var remaining = intValue(count);
    while (remaining > 0) {
      var bus = buses
        .filter(function(item) { return item.effective - item.used > 0; })
        .sort(function(a, b) { return (b.effective - b.used) - (a.effective - a.used); })[0];
      if (!bus) break;
      var existing = bus.items.find(function(item) { return item.type === 'extra' && item.name === name; });
      if (existing) existing.count += 1;
      else bus.items.push({ type: 'extra', name: name, count: 1 });
      bus.used += 1;
      remaining -= 1;
    }
    return remaining;
  }

  function buildSuggestion(input) {
    var classes = buildClasses(input);
    var classCount = classes.length || intValue(input.classCount);
    var studentCount = classes.length ? classes.reduce(function(sum, item) { return sum + item.students; }, 0) : intValue(input.studentCount);
    var teacherCount = classes.length ? classes.reduce(function(sum, item) { return sum + item.teachers; }, 0) : intValue(input.teacherCount);
    var leaderCount = intValue(input.leaderCount);
    var responsibleStaff = intValue(input.responsibleStaff);
    var projectStaff = intValue(input.projectStaff);
    var reserveSeats = Math.max(1, intValue(input.reserveSeats || 2));
    var splitStrategy = input.splitStrategy || (input.allowSplit === false ? 'forbid' : 'whole');
    if (['forbid', 'whole', 'balanced'].indexOf(splitStrategy) < 0) splitStrategy = 'whole';
    var warnings = [];

    if (studentCount <= 0 || classCount <= 0) {
      return {
        ok: false,
        message: '填写班级数和学生人数后自动生成分车建议。',
        warnings: warnings,
        buses: [],
        summary: { totalPeople: 0, busCount: 0, capacity: 0, surplus: 0, utilization: 0 }
      };
    }

    if (teacherCount < classCount) warnings.push('学校教师少于班级数，部分班级没有随班老师。');

    var basePeople = studentCount + teacherCount + leaderCount + projectStaff;
    var planOptions = {
      reserveSeats: reserveSeats,
      busTypes: input.busTypes || DEFAULT_BUS_TYPES,
      availableFleet: input.availableFleet
    };
    var planDetails = recommendBusesDetailed(basePeople, responsibleStaff, planOptions);
    var plan = planDetails.plan;
    if (!plan.length || planDetails.remaining > 0) {
      return {
        ok: false,
        message: input.availableFleet ? '混合车队可用座位不足，请增加车型、数量或改用统一车型方案。' : '当前车型座位不足，请调整车型。',
        warnings: warnings,
        buses: [],
        classes: classes,
        splitStrategy: splitStrategy,
        summary: { classCount: classCount, studentCount: studentCount, teacherCount: teacherCount, totalPeople: studentCount + teacherCount + leaderCount + projectStaff + responsibleStaff, busCount: plan.length, capacity: 0, surplus: 0, utilization: 0 }
      };
    }
    var wholeClasses = splitStrategy === 'forbid'
      ? classes
      : classes.filter(function(item) { return item.splitRule === 'forbid'; });
    plan = improveWholeClassPlan(plan, wholeClasses, planOptions);
    var additionalResponsible = Math.max(0, responsibleStaff - plan.length);
    if (responsibleStaff < plan.length) warnings.push('导游/教官少于车辆数，需补齐每车主随车负责人。');

    var buses = plan.map(function(seats, index) {
      return {
        index: index,
        num: index + 1,
        seats: seats,
        effective: effectiveSeats(seats, reserveSeats),
        used: 0,
        reservedNote: '司机及主负责人预留 ' + reserveSeats + ' 座',
        items: []
      };
    });

    classes = classes.slice().sort(function(a, b) {
      if (splitStrategy !== 'forbid' && a.splitRule !== b.splitRule) {
        if (a.splitRule === 'forbid') return -1;
        if (b.splitRule === 'forbid') return 1;
      }
      return (b.students + b.teachers) - (a.students + a.teachers);
    });
    var allocationValid = true;
    for (var i = 0; i < classes.length; i += 1) {
      var canSplit = splitStrategy !== 'forbid' && classes[i].splitRule !== 'forbid';
      if (!allocateClassAcrossBuses(classes[i], buses, canSplit)) {
        warnings.push(classes[i].name + '无法整班分配，建议增加车辆或允许拆班。');
        allocationValid = false;
      }
    }
    if (splitStrategy === 'balanced' && allocationValid) balanceClassAllocations(buses, classes);
    else markPartialClasses(buses);

    if (splitStrategy === 'balanced') {
      classes.forEach(function(cls) {
        if (cls.teachers <= 0) return;
        var needsTeacher = buses.some(function(bus) {
          return bus.items.some(function(item) { return item.type === 'class' && item.classId === cls.id && item.students > 0 && item.teachers <= 0; });
        });
        if (needsTeacher) warnings.push(cls.name + '拆分后有车辆未配置随班教师，请人工确认或补配负责人。');
      });
    }

    if (plan.indexOf(59) >= 0) warnings.push('方案使用59座车型，请提前向车队确认车辆供应。');

    var leftLeaders = distributeExtra('学校领导', leaderCount, buses);
    var leftProjectStaff = distributeExtra('项目人员', projectStaff, buses);
    var leftResponsible = distributeExtra('额外导游/教官', additionalResponsible, buses);
    if (leftLeaders + leftProjectStaff + leftResponsible > 0) warnings.push('当前车辆余座不足，请增加车辆。');

    var capacity = buses.reduce(function(sum, bus) { return sum + bus.effective; }, 0);
    var used = buses.reduce(function(sum, bus) { return sum + bus.used; }, 0);
    var required = basePeople + additionalResponsible;
    return {
      ok: true,
      valid: allocationValid && leftLeaders + leftProjectStaff + leftResponsible <= 0,
      warnings: warnings,
      buses: buses,
      classes: classes,
      splitStrategy: splitStrategy,
      summary: {
        classCount: classCount,
        studentCount: studentCount,
        teacherCount: teacherCount,
        totalPeople: studentCount + teacherCount + leaderCount + projectStaff + responsibleStaff,
        countedSeatPeople: required,
        busCount: buses.length,
        capacity: capacity,
        used: used,
        surplus: capacity - required,
        utilization: capacity > 0 ? Math.round(required / capacity * 100) : 0
      }
    };
  }

  function seedManualAssignments(result) {
    var assignments = {};
    (result.classes || []).forEach(function(cls) { assignments[cls.id] = {}; });
    (result.buses || []).forEach(function(bus) {
      bus.items.forEach(function(item) {
        if (item.type !== 'class') return;
        if (!assignments[item.classId]) assignments[item.classId] = {};
        assignments[item.classId][bus.index] = { students: intValue(item.students), teachers: intValue(item.teachers) };
      });
    });
    return assignments;
  }

  function applyManualAssignments(baseResult, assignments) {
    var result = JSON.parse(JSON.stringify(baseResult));
    var classes = result.classes || [];
    var errors = [];
    var warnings = (result.warnings || []).slice();
    result.buses.forEach(function(bus) {
      bus.items = bus.items.filter(function(item) { return item.type !== 'class'; });
      bus.used = bus.items.reduce(function(sum, item) { return sum + intValue(item.count); }, 0);
    });
    classes.forEach(function(cls) {
      var classAssignments = assignments && assignments[cls.id] || {};
      var totalStudents = 0;
      var totalTeachers = 0;
      var occupiedBuses = 0;
      result.buses.forEach(function(bus) {
        var cell = classAssignments[bus.index] || {};
        var students = intValue(cell.students);
        var teachers = intValue(cell.teachers);
        if (students + teachers <= 0) return;
        occupiedBuses += 1;
        totalStudents += students;
        totalTeachers += teachers;
        bus.items.push({
          type: 'class',
          classId: cls.id,
          name: cls.name,
          students: students,
          teachers: teachers,
          splitRule: cls.splitRule,
          partial: false
        });
        bus.used += students + teachers;
        if (students > 0 && teachers <= 0 && cls.teachers > 0) warnings.push(cls.name + '在' + bus.num + '号车没有随班教师，请人工确认。');
      });
      if (totalStudents !== cls.students) errors.push(cls.name + '学生合计应为' + cls.students + '人，当前为' + totalStudents + '人。');
      if (totalTeachers !== cls.teachers) errors.push(cls.name + '教师合计应为' + cls.teachers + '人，当前为' + totalTeachers + '人。');
      if (occupiedBuses > 1 && (result.splitStrategy === 'forbid' || cls.splitRule === 'forbid')) errors.push(cls.name + '当前禁止拆班，不能分到多辆车。');
    });
    result.buses.forEach(function(bus) {
      if (bus.used > bus.effective) errors.push(bus.num + '号车超出可排座位' + (bus.used - bus.effective) + '人。');
    });
    markPartialClasses(result.buses);
    result.summary.used = result.buses.reduce(function(sum, bus) { return sum + bus.used; }, 0);
    result.manual = true;
    result.manualErrors = errors;
    result.warnings = warnings.filter(function(item, index, list) { return list.indexOf(item) === index; });
    result.valid = errors.length === 0;
    return result;
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch];
    });
  }

  function ensureStyle() {
    if (typeof document === 'undefined' || document.getElementById('yaochengDispatchAdvisorStyle')) return;
    var style = document.createElement('style');
    style.id = 'yaochengDispatchAdvisorStyle';
    style.textContent = [
      '.dispatch-advisor{margin-top:14px;border:1px solid #cbd9e5;border-radius:8px;background:#fbfdff;padding:14px;color:#203248}',
      '.dispatch-advisor-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px}',
      '.dispatch-advisor-head h3{margin:0;font-size:15px}.dispatch-advisor-head p{margin:4px 0 0;color:#65768a;font-size:12px;line-height:1.6}',
      '.dispatch-advisor-controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:10px 0}',
      '.dispatch-advisor-controls label{display:grid;gap:5px;color:#65768a;font-size:11px;font-weight:750}.dispatch-advisor-controls input,.dispatch-advisor-controls select{min-height:38px;border:1px solid #d6e0eb;border-radius:8px;background:#fff;padding:7px 9px;color:#203248}',
      '.dispatch-advisor-toggle{display:flex!important;align-items:center;gap:7px}.dispatch-advisor-toggle input{min-height:auto;width:auto}',
      '.dispatch-plan-tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}.dispatch-plan-tab{display:grid;gap:3px;text-align:left;min-height:58px;padding:9px 11px;border:1px solid #cbd9e5;border-radius:8px;background:#fff;color:#203248;cursor:pointer}.dispatch-plan-tab.active{border-color:#2563eb;background:#eef3ff;color:#1d4ed8}.dispatch-plan-tab b{font-size:13px}.dispatch-plan-tab span{font-size:11px;color:#65768a}',
      '.dispatch-fleet{margin:10px 0;border:1px solid #dbe5f0;border-radius:8px;background:#fff;padding:10px}.dispatch-fleet summary{cursor:pointer;font-size:12px;font-weight:900;color:#3157c8}.dispatch-fleet-note{margin:7px 0;color:#65768a;font-size:11px}.dispatch-fleet-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.dispatch-fleet-row{display:grid;grid-template-columns:auto minmax(70px,1fr) minmax(76px,1fr) auto;align-items:center;gap:7px;padding:7px;border:1px solid #edf2f7;border-radius:8px}.dispatch-fleet-row input[type="checkbox"]{width:18px;height:18px}.dispatch-fleet-row input[type="number"]{width:100%;min-width:0;min-height:34px;border:1px solid #d6e0eb;border-radius:7px;padding:5px 7px}.dispatch-fleet-remove{width:30px;height:30px;border:1px solid #fecaca;border-radius:7px;background:#fff;color:#b42318;cursor:pointer}.dispatch-fleet-add{margin-top:8px;min-height:34px;border:1px solid #cbd9e5;border-radius:8px;background:#fff;color:#203248;font-weight:800;cursor:pointer}',
      '.dispatch-advisor-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.dispatch-advisor-actions button,.dispatch-advisor-actions a{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:7px 11px;border-radius:8px;border:1px solid #cbd9e5;background:#fff;color:#203248;font-weight:800;text-decoration:none;cursor:pointer}.dispatch-advisor-actions .primary{background:#2563eb;border-color:#2563eb;color:#fff}',
      '.dispatch-advisor-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.dispatch-advisor-metric{border:1px solid #e3ebf2;border-radius:8px;background:#f5f8fb;padding:9px}.dispatch-advisor-metric span{display:block;color:#65768a;font-size:11px}.dispatch-advisor-metric b{display:block;margin-top:3px;font-size:16px}',
      '.dispatch-advisor-warning{margin:7px 0;padding:8px 10px;border-radius:8px;background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;font-size:12px;line-height:1.6}',
      '.dispatch-advisor-error{margin:7px 0;padding:8px 10px;border-radius:8px;background:#fff1f2;border:1px solid #fecdd3;color:#b42318;font-size:12px;line-height:1.6}',
      '.dispatch-advisor-empty{margin-top:8px;padding:12px;border:1px dashed #cbd9e5;border-radius:8px;color:#65768a;background:#f7fafc;font-size:12px}',
      '.dispatch-advisor-buses{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}.dispatch-advisor-bus{border:1px solid #dbe5f0;border-radius:8px;background:#fff;overflow:hidden}.dispatch-advisor-bus-head{display:flex;justify-content:space-between;gap:8px;padding:8px 10px;background:#eef3ff;color:#1d4ed8;font-weight:900;font-size:12px}.dispatch-advisor-bus-body{padding:8px 10px;display:grid;gap:6px}.dispatch-advisor-row{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid #edf2f7;padding-bottom:5px;font-size:12px}.dispatch-advisor-row:last-child{border-bottom:0}.dispatch-advisor-row small{color:#65768a}.dispatch-advisor-foot{display:flex;justify-content:space-between;gap:8px;padding:8px 10px;border-top:1px solid #edf2f7;color:#65768a;font-size:11px}',
      '.dispatch-manual{margin-top:10px;border:1px solid #dbe5f0;border-radius:8px;background:#fff;padding:10px}.dispatch-manual-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.dispatch-manual-head h4{margin:0;font-size:13px}.dispatch-manual-head p{margin:3px 0 0;color:#65768a;font-size:11px}.dispatch-manual-actions{display:flex;flex-wrap:wrap;gap:7px}.dispatch-manual-actions button{min-height:34px;border:1px solid #cbd9e5;border-radius:8px;background:#fff;color:#203248;font-weight:800;cursor:pointer}.dispatch-manual-table-wrap{margin-top:8px;max-width:100%;overflow:auto}.dispatch-manual-table{width:100%;min-width:640px;border-collapse:collapse;font-size:11px}.dispatch-manual-table th,.dispatch-manual-table td{padding:6px;border:1px solid #edf2f7;text-align:center}.dispatch-manual-table th{background:#f5f8fb}.dispatch-manual-cell{display:grid;grid-template-columns:repeat(2,minmax(54px,1fr));gap:4px}.dispatch-manual-cell label{display:grid;gap:2px;color:#65768a}.dispatch-manual-cell input{width:100%;min-width:0;min-height:32px;border:1px solid #d6e0eb;border-radius:6px;padding:4px 6px}',
      '.dispatch-execution{margin-top:10px;border:1px solid #dbe5f0;border-radius:8px;background:#fff;padding:10px}.dispatch-execution-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.dispatch-execution-head h4{margin:0;font-size:13px}.dispatch-execution-head p{margin:3px 0 0;color:#65768a;font-size:11px;line-height:1.5}.dispatch-execution-status{font-size:11px;font-weight:800;color:#9a3412}.dispatch-execution-status.ready{color:#087443}.dispatch-execution-list{display:grid;gap:8px;margin-top:9px}.dispatch-execution-row{border:1px solid #edf2f7;border-radius:8px;padding:9px}.dispatch-execution-row-head{display:flex;justify-content:space-between;gap:8px;margin-bottom:7px;color:#3157c8;font-size:12px;font-weight:900}.dispatch-execution-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.dispatch-execution-fields label{display:grid;gap:4px;color:#65768a;font-size:11px;font-weight:750}.dispatch-execution-fields label.required span:after{content:" *";color:#b42318}.dispatch-execution-fields input{width:100%;min-width:0;min-height:34px;border:1px solid #d6e0eb;border-radius:7px;background:#fff;padding:6px 8px;color:#203248}',
      '.dispatch-print-report{display:none}',
      '@media print{body.dispatch-printing{background:#fff!important;color:#111!important;padding:0!important}body.dispatch-printing>*:not(.dispatch-print-report){display:none!important}body.dispatch-printing .dispatch-print-report{display:block!important;font-family:"PingFang SC","Microsoft YaHei",Arial,sans-serif;color:#111;font-size:10.5pt;line-height:1.45}body.dispatch-printing .dispatch-print-page{display:block!important;page-break-after:always;break-after:page;min-height:260mm}body.dispatch-printing .dispatch-print-page:last-child{page-break-after:auto;break-after:auto}body.dispatch-printing .dispatch-print-header{display:flex!important;align-items:flex-end;justify-content:space-between;gap:16px;border-bottom:2px solid #111;padding-bottom:8px;margin-bottom:12px}body.dispatch-printing .dispatch-print-header h1{margin:0;font-size:20pt;letter-spacing:0}body.dispatch-printing .dispatch-print-header p{margin:3px 0 0;color:#444}body.dispatch-printing .dispatch-print-brand{text-align:right;font-size:9pt;color:#444}body.dispatch-printing .dispatch-print-meta{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:0;border:1px solid #777;margin-bottom:12px}body.dispatch-printing .dispatch-print-meta div{display:grid!important;grid-template-columns:82px 1fr;min-height:32px;border-bottom:1px solid #aaa}body.dispatch-printing .dispatch-print-meta div:nth-last-child(-n+2){border-bottom:0}body.dispatch-printing .dispatch-print-meta div:nth-child(odd){border-right:1px solid #aaa}body.dispatch-printing .dispatch-print-meta span{padding:7px 8px;background:#f2f2f2;font-weight:700}body.dispatch-printing .dispatch-print-meta b{padding:7px 8px;font-weight:500}body.dispatch-printing .dispatch-print-table{width:100%;border-collapse:collapse;table-layout:fixed;margin-bottom:12px}body.dispatch-printing .dispatch-print-table th,body.dispatch-printing .dispatch-print-table td{border:1px solid #777;padding:6px 7px;text-align:left;vertical-align:top;word-break:break-word}body.dispatch-printing .dispatch-print-table th{background:#ededed;font-weight:700}body.dispatch-printing .dispatch-print-table .center{text-align:center}body.dispatch-printing .dispatch-print-note{border:1px solid #777;padding:8px 10px;margin:10px 0}body.dispatch-printing .dispatch-print-note b{display:block;margin-bottom:4px}body.dispatch-printing .dispatch-print-sign{display:grid!important;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:18px}body.dispatch-printing .dispatch-print-sign div{border-bottom:1px solid #555;padding:10px 2px 4px}body.dispatch-printing .dispatch-print-fields{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 18px;border:1px solid #777;padding:12px;margin:12px 0}body.dispatch-printing .dispatch-print-fields div{min-height:28px;border-bottom:1px solid #777;padding:4px 2px}body.dispatch-printing .dispatch-print-checks{display:grid!important;grid-template-columns:repeat(2,1fr);gap:8px 16px;border:1px solid #777;padding:12px;margin-top:12px}body.dispatch-printing .dispatch-print-checks span{white-space:nowrap}}',
      '.class-roster{margin-top:14px;border-top:1px solid #e3ebf2;padding-top:14px}.class-roster-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.class-roster-head h3{margin:0;font-size:15px}.class-roster-head p{margin:4px 0 0;color:#65768a;font-size:12px;line-height:1.6}.class-roster-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}.class-roster-actions button,.class-roster-file-label{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:7px 11px;border:1px solid #cbd9e5;border-radius:8px;background:#fff;color:#203248;font-weight:800;font-size:12px;cursor:pointer}.class-roster-file-label{background:#2563eb;border-color:#2563eb;color:#fff}.class-roster-file-label input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}.class-roster-status{margin-top:9px;min-height:18px;color:#65768a;font-size:12px}.class-roster-status.error{color:#b42318}.class-roster-summary{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}.class-roster-summary span{padding:6px 9px;border-radius:8px;background:#eef3ff;color:#3157c8;font-size:12px;font-weight:800}.class-roster-table-wrap{margin-top:10px;max-width:100%;overflow:auto;border:1px solid #dbe5f0;border-radius:8px}.class-roster-table{width:100%;min-width:700px;border-collapse:collapse;font-size:12px}.class-roster-table th,.class-roster-table td{padding:7px 8px;border-bottom:1px solid #edf2f7;text-align:left}.class-roster-table th{background:#f5f8fb;color:#536276;font-size:11px}.class-roster-table tr:last-child td{border-bottom:0}.class-roster-table input[type="text"],.class-roster-table input[type="number"],.class-roster-table select{width:100%;min-height:34px;border:1px solid #d6e0eb;border-radius:7px;background:#fff;padding:6px 8px;color:#203248}.class-roster-remove{width:32px;height:32px;border:1px solid #fecaca;border-radius:7px;background:#fff;color:#b42318;font-size:18px;cursor:pointer}.class-roster-empty{margin-top:10px;padding:13px;border:1px dashed #cbd9e5;border-radius:8px;background:#f7fafc;color:#65768a;font-size:12px}',
      '@media(max-width:900px){.dispatch-advisor-controls,.dispatch-advisor-summary,.dispatch-advisor-buses,.dispatch-fleet-grid,.dispatch-execution-fields{grid-template-columns:1fr}.dispatch-advisor-head,.class-roster-head,.dispatch-manual-head,.dispatch-execution-head{flex-direction:column}.dispatch-advisor-actions button,.class-roster-actions,.class-roster-actions button,.class-roster-file-label{width:100%}}'
    ].join('');
    document.head.appendChild(style);
  }

  function readMountedInput(rootEl, selector, fallback) {
    var el = rootEl.querySelector(selector);
    return el ? el.value : fallback;
  }

  function rosterSummary(classes) {
    return {
      classCount: classes.length,
      studentCount: classes.reduce(function(sum, item) { return sum + intValue(item.students); }, 0),
      teacherCount: classes.reduce(function(sum, item) { return sum + intValue(item.teachers); }, 0)
    };
  }

  function normalizeExecutionRows(rows, buses) {
    var source = Array.isArray(rows) ? rows : [];
    return (buses || []).map(function(bus, index) {
      var row = source[index] || {};
      return {
        busNum: intValue(bus && bus.num) || index + 1,
        seats: intValue(bus && bus.seats),
        plate: String(row.plate || '').trim(),
        driverName: String(row.driverName || '').trim(),
        driverPhone: String(row.driverPhone || '').trim(),
        responsible: String(row.responsible || '').trim(),
        meetingTime: String(row.meetingTime || '').trim(),
        boardingLocation: String(row.boardingLocation || '').trim()
      };
    });
  }

  function validateExecutionRows(result, rows) {
    if (!result || !result.ok || result.valid === false) return { ok: false, errors: ['当前分车方案仍有冲突，暂不能生成最终执行单。'] };
    var normalized = normalizeExecutionRows(rows, result.buses);
    var errors = normalized.filter(function(row) { return !row.responsible; }).map(function(row) {
      return row.busNum + '号车未填写随车负责人。';
    });
    return { ok: errors.length === 0, errors: errors, rows: normalized };
  }

  function templateWorkbookRows() {
    return [
      ['序号', '班级名称', '学生人数', '随班教师人数', '允许拆班', '备注'],
      [1, '一年一班', 45, 2, '禁止', ''],
      [2, '一年二班', 43, 2, '跟随', '可填写：跟随、禁止、允许']
    ];
  }

  function downloadClassTemplate() {
    if (typeof XLSX === 'undefined') throw new Error('Excel组件未就绪，请刷新页面后重试。');
    var sheet = XLSX.utils.aoa_to_sheet(templateWorkbookRows());
    sheet['!cols'] = [{wch: 8}, {wch: 18}, {wch: 14}, {wch: 18}, {wch: 14}, {wch: 28}];
    var workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, sheet, '班级信息');
    XLSX.writeFile(workbook, '曜程班级导入模板.xlsx');
  }

  function mountClassRoster(config) {
    if (typeof document === 'undefined') return null;
    ensureStyle();
    var container = document.getElementById(config.containerId);
    if (!container) return null;
    var classes = [];
    container.innerHTML =
      '<div class="class-roster-head"><div><h3>班级明细</h3><p>下载模板填写后导入，系统自动汇总班级、学生和随班教师，并立即生成分车方案。</p></div>' +
      '<div class="class-roster-actions"><button type="button" data-role="template">下载Excel模板</button><label class="class-roster-file-label">导入Excel<input data-role="file" type="file" accept=".xlsx,.xls"></label><button type="button" data-role="add">添加班级</button><button type="button" data-role="clear">清空</button></div></div>' +
      '<div class="class-roster-status" data-role="status"></div><div data-role="content"></div>';

    function status(message, isError) {
      var box = container.querySelector('[data-role="status"]');
      box.textContent = message || '';
      box.classList.toggle('error', !!isError);
    }

    function render() {
      var content = container.querySelector('[data-role="content"]');
      if (!classes.length) {
        content.innerHTML = '<div class="class-roster-empty">尚未导入班级表。也可以先手工填写汇总人数，分车建议仍会实时计算。</div>';
        return;
      }
      var summary = rosterSummary(classes);
      var summaryHtml = '<div class="class-roster-summary"><span>' + summary.classCount + ' 个班</span><span>学生 ' + summary.studentCount + ' 人</span><span>随班教师 ' + summary.teacherCount + ' 人</span></div>';
      var rows = classes.map(function(item, index) {
        var splitOptions = [['follow','跟随整体'],['forbid','禁止拆班'],['allow','允许拆班']].map(function(option) {
          return '<option value="' + option[0] + '" ' + (item.splitRule === option[0] ? 'selected' : '') + '>' + option[1] + '</option>';
        }).join('');
        return '<tr data-index="' + index + '"><td>' + (index + 1) + '</td><td><input type="text" data-field="name" value="' + escapeHtml(item.name) + '" aria-label="班级名称"></td><td><input type="number" min="1" data-field="students" value="' + item.students + '" aria-label="学生人数"></td><td><input type="number" min="0" data-field="teachers" value="' + item.teachers + '" aria-label="随班教师人数"></td><td><select data-field="splitRule" aria-label="拆班规则">' + splitOptions + '</select></td><td><input type="text" data-field="note" value="' + escapeHtml(item.note) + '" aria-label="备注"></td><td><button type="button" class="class-roster-remove" data-role="remove" title="删除班级" aria-label="删除' + escapeHtml(item.name) + '">×</button></td></tr>';
      }).join('');
      content.innerHTML = summaryHtml + '<div class="class-roster-table-wrap"><table class="class-roster-table"><thead><tr><th>序号</th><th>班级名称</th><th>学生人数</th><th>随班教师</th><th>拆班规则</th><th>备注</th><th>操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    }

    function updateRenderedSummary() {
      var spans = container.querySelectorAll('.class-roster-summary span');
      if (spans.length !== 3) return;
      var summary = rosterSummary(classes);
      spans[0].textContent = summary.classCount + ' 个班';
      spans[1].textContent = '学生 ' + summary.studentCount + ' 人';
      spans[2].textContent = '随班教师 ' + summary.teacherCount + ' 人';
    }

    function emitChange(options) {
      var summary = rosterSummary(classes);
      if (typeof config.applyTotals === 'function' && classes.length) config.applyTotals(summary);
      if (typeof config.onChange === 'function') config.onChange(classes.map(function(item) { return Object.assign({}, item); }), options || {});
    }

    function setClasses(nextClasses, options) {
      classes = normalizeClasses(nextClasses).map(function(item, index) {
        item.id = index + 1;
        return item;
      });
      render();
      emitChange(options || {});
      return classes;
    }

    function addClass() {
      classes.push({ id: classes.length + 1, name: '新班级' + (classes.length + 1), students: 1, teachers: 0, splitRule: 'follow', allowSplit: true, note: '' });
      render();
      emitChange();
      status('已添加班级，请完善人数。', false);
    }

    container.querySelector('[data-role="template"]').addEventListener('click', function() {
      try { downloadClassTemplate(); status('模板已下载。', false); }
      catch (error) { status(error.message, true); }
    });
    container.querySelector('[data-role="add"]').addEventListener('click', addClass);
    container.querySelector('[data-role="clear"]').addEventListener('click', function() {
      if (!classes.length) return;
      if (typeof window !== 'undefined' && !window.confirm('确定清空已导入的班级明细吗？')) return;
      classes = [];
      render();
      emitChange();
      status('班级明细已清空，汇总人数可继续手工填写。', false);
    });
    container.querySelector('[data-role="file"]').addEventListener('change', function(event) {
      var input = event.target;
      var file = input.files && input.files[0];
      if (!file) return;
      if (!/\.(xlsx|xls)$/i.test(file.name || '')) {
        status('仅支持 .xlsx 或 .xls 班级表。', true);
        input.value = '';
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        status('Excel文件不能超过5MB，请删除无关图片或拆分后重试。', true);
        input.value = '';
        return;
      }
      status('正在解析“' + file.name + '”...', false);
      var reader = new FileReader();
      reader.onload = function(loadEvent) {
        try {
          if (typeof XLSX === 'undefined') throw new Error('Excel组件未就绪，请刷新页面后重试。');
          var workbook = XLSX.read(new Uint8Array(loadEvent.target.result), { type: 'array' });
          if (!workbook.SheetNames || !workbook.SheetNames.length) throw new Error('Excel中没有可读取的工作表。');
          var sheet = workbook.Sheets[workbook.SheetNames[0]];
          var parsed = parseClassRows(XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' }));
          if (parsed.errors.length) {
            var visibleErrors = parsed.errors.slice(0, 5).join('；');
            if (parsed.errors.length > 5) visibleErrors += '；另有' + (parsed.errors.length - 5) + '处错误';
            throw new Error(visibleErrors);
          }
          if (classes.length && typeof window !== 'undefined' && !window.confirm('导入会替换当前班级明细，确定继续吗？')) return;
          setClasses(parsed.classes);
          status('成功导入 ' + parsed.classes.length + ' 个班级，分车方案已自动更新。', false);
        } catch (error) {
          status(error.message || 'Excel解析失败，请检查模板内容。', true);
        } finally {
          input.value = '';
        }
      };
      reader.onerror = function() { status('文件读取失败，请重新选择。', true); input.value = ''; };
      reader.readAsArrayBuffer(file);
    });
    container.addEventListener('input', function(event) {
      var row = event.target.closest('tr[data-index]');
      if (!row) return;
      var index = intValue(row.dataset.index);
      var field = event.target.dataset.field;
      if (!classes[index] || !field) return;
      if (field === 'students' || field === 'teachers') classes[index][field] = intValue(event.target.value);
      else if (field === 'splitRule') {
        classes[index].splitRule = normalizeSplitRule(event.target.value);
        classes[index].allowSplit = classes[index].splitRule !== 'forbid';
      }
      else classes[index][field] = event.target.value;
      updateRenderedSummary();
      emitChange();
      status('班级明细已修改，分车方案已自动更新。', false);
    });
    container.addEventListener('change', function(event) {
      if (event.target.dataset.field !== 'splitRule') return;
      var row = event.target.closest('tr[data-index]');
      var index = row ? intValue(row.dataset.index) : -1;
      if (classes[index]) {
        classes[index].splitRule = normalizeSplitRule(event.target.value);
        classes[index].allowSplit = classes[index].splitRule !== 'forbid';
      }
      updateRenderedSummary();
      emitChange();
    });
    container.addEventListener('click', function(event) {
      var button = event.target.closest('[data-role="remove"]');
      if (!button) return;
      var row = button.closest('tr[data-index]');
      var index = row ? intValue(row.dataset.index) : -1;
      if (!classes[index]) return;
      classes.splice(index, 1);
      render();
      emitChange();
      status('班级已删除，汇总和分车方案已更新。', false);
    });
    render();
    return {
      getClasses: function() { return classes.map(function(item) { return Object.assign({}, item); }); },
      setClasses: setClasses,
      clear: function(options) { classes = []; render(); emitChange(options || {}); },
      downloadTemplate: downloadClassTemplate,
      container: container
    };
  }

  function renderResult(result) {
    if (!result.ok) return '<div class="dispatch-advisor-empty">' + escapeHtml(result.message) + '</div>';
    var errors = result.manualErrors && result.manualErrors.length
      ? '<div class="dispatch-advisor-error">' + result.manualErrors.map(escapeHtml).join('<br>') + '</div>'
      : (result.valid === false ? '<div class="dispatch-advisor-error">当前方案仍有未完成分配，暂不能计入交通费。</div>' : '');
    var warnings = result.warnings.length
      ? '<div class="dispatch-advisor-warning">' + result.warnings.map(escapeHtml).join('<br>') + '</div>'
      : '';
    var summary = [
      ['总人数', result.summary.totalPeople + ' 人'],
      ['车辆建议', result.summary.busCount + ' 辆'],
      ['可排余座', result.summary.surplus + ' 座'],
      ['满载率', result.summary.utilization + '%']
    ].map(function(item) {
      return '<div class="dispatch-advisor-metric"><span>' + item[0] + '</span><b>' + item[1] + '</b></div>';
    }).join('');
    var buses = result.buses.map(function(bus) {
      var rows = bus.items.length ? bus.items.map(function(item) {
        if (item.type === 'class') {
          return '<div class="dispatch-advisor-row"><span>' + escapeHtml(item.name) + (item.partial ? ' <small>拆分</small>' : '') + '</span><b>学生' + item.students + ' · 教师' + item.teachers + '</b></div>';
        }
        return '<div class="dispatch-advisor-row"><span>' + escapeHtml(item.name) + '</span><b>' + item.count + '人</b></div>';
      }).join('') : '<div class="dispatch-advisor-row"><span>待安排</span><b>0人</b></div>';
      return '<div class="dispatch-advisor-bus"><div class="dispatch-advisor-bus-head"><span>' + bus.num + '号车</span><span>' + bus.seats + '座</span></div><div class="dispatch-advisor-bus-body">' + rows + '</div><div class="dispatch-advisor-foot"><span>' + escapeHtml(bus.reservedNote) + '</span><b>乘员 ' + bus.used + '/' + bus.effective + '</b></div></div>';
    }).join('');
    return errors + warnings + '<div class="dispatch-advisor-summary">' + summary + '</div><div class="dispatch-advisor-buses">' + buses + '</div>';
  }

  function renderExecutionEditor(result, executionRows) {
    if (!result.ok || !result.buses.length) return '';
    var rows = normalizeExecutionRows(executionRows, result.buses);
    var check = validateExecutionRows(result, rows);
    var missing = rows.filter(function(row) { return !row.responsible; }).length;
    var status = result.valid === false
      ? '请先处理分车冲突'
      : missing
      ? '还有' + missing + '辆车未填随车负责人'
      : '已满足执行单打印条件';
    var content = rows.map(function(row, index) {
      return '<div class="dispatch-execution-row" data-execution-index="' + index + '">' +
        '<div class="dispatch-execution-row-head"><span>' + row.busNum + '号车</span><span>' + row.seats + '座</span></div>' +
        '<div class="dispatch-execution-fields">' +
          '<label><span>车牌号</span><input maxlength="20" value="' + escapeHtml(row.plate) + '" data-execution-field="plate" aria-label="' + row.busNum + '号车车牌号"></label>' +
          '<label><span>司机姓名</span><input maxlength="30" value="' + escapeHtml(row.driverName) + '" data-execution-field="driverName" aria-label="' + row.busNum + '号车司机姓名"></label>' +
          '<label><span>司机电话</span><input type="tel" maxlength="30" value="' + escapeHtml(row.driverPhone) + '" data-execution-field="driverPhone" aria-label="' + row.busNum + '号车司机电话"></label>' +
          '<label class="required"><span>随车负责人（教师/导游/教官）</span><input maxlength="30" value="' + escapeHtml(row.responsible) + '" data-execution-field="responsible" aria-label="' + row.busNum + '号车随车负责人"></label>' +
          '<label><span>集合时间</span><input maxlength="40" placeholder="例如 07:30" value="' + escapeHtml(row.meetingTime) + '" data-execution-field="meetingTime" aria-label="' + row.busNum + '号车集合时间"></label>' +
          '<label><span>上车地点</span><input maxlength="80" value="' + escapeHtml(row.boardingLocation) + '" data-execution-field="boardingLocation" aria-label="' + row.busNum + '号车上车地点"></label>' +
        '</div></div>';
    }).join('');
    return '<section class="dispatch-execution"><div class="dispatch-execution-head"><div><h4>车辆执行信息</h4><p>报价和计入交通费不受影响；打印最终分车执行单前，每车必须明确一名随车负责人。</p></div><div class="dispatch-execution-status ' + (check.ok ? 'ready' : '') + '" data-role="execution-status">' + status + '</div></div><div class="dispatch-execution-list">' + content + '</div></section>';
  }

  function renderManualEditor(result, assignments) {
    if (!result.ok || !result.buses.length) return '';
    var headers = result.buses.map(function(bus) { return '<th>' + bus.num + '号车<br>' + bus.seats + '座</th>'; }).join('');
    var rows = (result.classes || []).map(function(cls) {
      var cells = result.buses.map(function(bus) {
        var value = assignments && assignments[cls.id] && assignments[cls.id][bus.index] || {};
        return '<td><div class="dispatch-manual-cell">' +
          '<label>学生<input type="number" min="0" max="' + cls.students + '" value="' + intValue(value.students) + '" data-manual-class="' + escapeHtml(cls.id) + '" data-manual-bus="' + bus.index + '" data-manual-field="students" aria-label="' + escapeHtml(cls.name) + bus.num + '号车学生"></label>' +
          '<label>教师<input type="number" min="0" max="' + cls.teachers + '" value="' + intValue(value.teachers) + '" data-manual-class="' + escapeHtml(cls.id) + '" data-manual-bus="' + bus.index + '" data-manual-field="teachers" aria-label="' + escapeHtml(cls.name) + bus.num + '号车教师"></label>' +
          '</div></td>';
      }).join('');
      return '<tr><th>' + escapeHtml(cls.name) + '<br><small>学生' + cls.students + ' · 教师' + cls.teachers + '</small></th>' + cells + '</tr>';
    }).join('');
    return '<div class="dispatch-manual"><div class="dispatch-manual-head"><div><h4>人工调整分车人数</h4><p>修改后点击校验；红色提示消失后才能确认方案。</p></div><div class="dispatch-manual-actions"><button type="button" data-role="manual-validate">校验调整</button><button type="button" data-role="manual-reset">恢复自动分配</button></div></div>' +
      '<div class="dispatch-manual-table-wrap"><table class="dispatch-manual-table"><thead><tr><th>班级</th>' + headers + '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
  }

  function printStrategyLabel(strategy) {
    return strategy === 'forbid' ? '禁止拆班' : strategy === 'balanced' ? '灵活混排' : '整班优先';
  }

  function buildPrintReportHtml(result, options) {
    options = options || {};
    var meta = options.meta || {};
    var source = options.source || {};
    var planName = options.planName || '统一车型';
    var printedAt = options.printedAt || new Date().toLocaleString();
    var classMap = {};
    (result.classes || []).forEach(function(cls) { classMap[String(cls.id)] = cls; });
    var responsibleStaff = intValue(source.responsibleStaff);
    var primaryResponsibleCount = Math.min(responsibleStaff, (result.buses || []).length);
    var executionRows = normalizeExecutionRows(options.executionRows, result.buses);

    function executionFor(bus) {
      return executionRows[bus.index] || normalizeExecutionRows([], [bus])[0];
    }

    function value(input, fallback) {
      var text = String(input == null ? '' : input).trim();
      return escapeHtml(text || fallback || '');
    }

    function itemText(item) {
      if (item.type === 'class') return escapeHtml(item.name) + (item.partial ? '（拆分）' : '');
      return escapeHtml(item.name) + ' ' + intValue(item.count) + '人';
    }

    function classRows(bus) {
      var rows = bus.items.filter(function(item) { return item.type === 'class'; }).map(function(item) {
        var cls = classMap[String(item.classId)] || {};
        return '<tr><td>' + escapeHtml(item.name) + (item.partial ? '（拆分）' : '') + '</td><td class="center">' + intValue(item.students) + '</td><td class="center">' + intValue(item.teachers) + '</td><td>' + value(cls.note, '') + '</td></tr>';
      });
      bus.items.filter(function(item) { return item.type !== 'class'; }).forEach(function(item) {
        rows.push('<tr><td>' + escapeHtml(item.name) + '</td><td class="center">-</td><td class="center">-</td><td>' + intValue(item.count) + '人</td></tr>');
      });
      var execution = executionFor(bus);
      if (execution.responsible || bus.index < primaryResponsibleCount) rows.push('<tr><td>主随车负责人</td><td class="center">-</td><td class="center">-</td><td>' + value(execution.responsible, '1人') + '，使用预留座</td></tr>');
      return rows.join('') || '<tr><td colspan="4">待安排</td></tr>';
    }

    var overviewRows = (result.buses || []).map(function(bus) {
      var classItems = bus.items.filter(function(item) { return item.type === 'class'; });
      var studentCount = classItems.reduce(function(sum, item) { return sum + intValue(item.students); }, 0);
      var teacherCount = classItems.reduce(function(sum, item) { return sum + intValue(item.teachers); }, 0);
      var extras = bus.items.filter(function(item) { return item.type !== 'class'; }).map(itemText);
      var execution = executionFor(bus);
      if (execution.responsible || bus.index < primaryResponsibleCount) extras.unshift('主负责人：' + value(execution.responsible, '1人'));
      var vehicle = [execution.plate, execution.driverName, execution.driverPhone].filter(function(item) { return !!item; }).map(escapeHtml).join('<br>');
      return '<tr><td class="center">' + bus.num + '号车</td><td class="center">' + bus.seats + '座</td><td>' + classItems.map(itemText).join('、') + '</td><td class="center">' + studentCount + '</td><td class="center">' + teacherCount + '</td><td>' + (extras.join('、') || '-') + '</td><td class="center">' + bus.used + '/' + bus.effective + '</td><td>' + (vehicle || '____________') + '</td></tr>';
    }).join('');
    var warnings = (result.warnings || []).length
      ? '<div class="dispatch-print-note"><b>注意事项</b>' + result.warnings.map(escapeHtml).join('<br>') + '</div>'
      : '';
    var summaryPage = '<section class="dispatch-print-page dispatch-print-overview">' +
      '<div class="dispatch-print-header"><div><h1>曜程分车执行单</h1><p>' + value(meta.moduleName, '研学项目') + ' · ' + value(planName) + ' · ' + value(printStrategyLabel(result.splitStrategy)) + '</p></div><div class="dispatch-print-brand">新未来（天津）教育科技有限公司<br>生成时间：' + value(printedAt) + '</div></div>' +
      '<div class="dispatch-print-meta"><div><span>项目名称</span><b>' + value(meta.projectName, '未填写') + '</b></div><div><span>学校/客户</span><b>' + value(meta.customerName, '未关联') + '</b></div><div><span>活动日期</span><b>' + value(meta.activityDate, '待确定') + '</b></div><div><span>车辆建议</span><b>' + intValue(result.summary.busCount) + '辆</b></div><div><span>人员汇总</span><b>学生' + intValue(result.summary.studentCount) + '人 · 教师' + intValue(result.summary.teacherCount) + '人 · 随行总人数' + intValue(result.summary.totalPeople) + '人</b></div><div><span>司机人数</span><b>' + intValue(result.summary.busCount) + '人</b></div></div>' +
      '<table class="dispatch-print-table"><colgroup><col style="width:7%"><col style="width:7%"><col style="width:25%"><col style="width:7%"><col style="width:7%"><col style="width:20%"><col style="width:10%"><col style="width:17%"></colgroup><thead><tr><th>车号</th><th>车型</th><th>班级安排</th><th>学生</th><th>教师</th><th>其他人员</th><th>正常占座</th><th>车牌/司机</th></tr></thead><tbody>' + overviewRows + '</tbody></table>' + warnings +
      '<div class="dispatch-print-sign"><div>计调签字：</div><div>审核签字：</div><div>确认日期：</div></div></section>';

    var busPages = (result.buses || []).map(function(bus) {
      var execution = executionFor(bus);
      var primaryText = execution.responsible ? '随车负责人：' + execution.responsible : (bus.index < primaryResponsibleCount ? '已预留1名主随车负责人' : '未配置主随车负责人');
      return '<section class="dispatch-print-page dispatch-print-bus-page"><div class="dispatch-print-header"><div><h1>' + bus.num + '号车执行单</h1><p>' + value(meta.projectName, '未填写项目') + ' · ' + value(meta.activityDate, '日期待定') + '</p></div><div class="dispatch-print-brand">' + bus.seats + '座 · 正常占座 ' + bus.used + '/' + bus.effective + '<br>' + value(primaryText) + '</div></div>' +
        '<div class="dispatch-print-fields"><div>车牌号：' + value(execution.plate, '____________') + '</div><div>司机姓名：' + value(execution.driverName, '____________') + '</div><div>司机电话：' + value(execution.driverPhone, '____________') + '</div><div>随车负责人：' + value(execution.responsible, '____________') + '</div><div>集合时间：' + value(execution.meetingTime, '____________') + '</div><div>上车地点：' + value(execution.boardingLocation, '____________') + '</div></div>' +
        '<table class="dispatch-print-table"><thead><tr><th>班级/人员</th><th style="width:16%">学生</th><th style="width:16%">教师</th><th style="width:30%">备注</th></tr></thead><tbody>' + classRows(bus) + '</tbody></table>' +
        '<div class="dispatch-print-note"><b>座位说明</b>' + value(bus.reservedNote) + '；正常占座' + bus.used + '人，可用' + bus.effective + '座。</div>' +
        '<div class="dispatch-print-checks"><span>□ 上车前人数已核对</span><span>□ 随班教师已到位</span><span>□ 司机与车牌已核对</span><span>□ 安全与紧急联系信息已确认</span></div>' +
        '<div class="dispatch-print-sign"><div>随车负责人签字：</div><div>司机签字：</div><div>实际上车人数：</div></div></section>';
    }).join('');
    return summaryPage + busPages;
  }

  function mount(config) {
    if (typeof document === 'undefined') return null;
    ensureStyle();
    var container = document.getElementById(config.containerId);
    if (!container) return null;
    var initialSeat = config.defaultSeat || 55;
    var initialReserve = config.reserveSeats || 2;
    var activePlan = 'uniform';
    var mixedFleet = DEFAULT_BUS_TYPES.map(function(seats) { return { seats: seats, enabled: true, count: null, custom: false }; });
    var manualByPlan = { uniform: null, mixed: null };
    var executionByPlan = { uniform: [], mixed: [] };
    var latestAuto = { uniform: null, mixed: null };
    var latestResult = null;
    var datalistId = config.containerId + 'SeatOptions';
    var seatOptions = DEFAULT_BUS_TYPES.map(function(seats) { return '<option value="' + seats + '"></option>'; }).join('');
    container.innerHTML =
      '<div class="dispatch-advisor-head"><div><h3>派车宝自动分车</h3><p>同时比较统一车型与混合车队；拆班策略和人工调整都在当前页面完成。</p></div><div class="dispatch-advisor-state" data-role="state">系统建议</div></div>' +
      '<div class="dispatch-advisor-controls">' +
        '<label>统一车型<input data-role="uniform-seat" type="number" min="7" max="80" value="' + initialSeat + '" list="' + datalistId + '"><datalist id="' + datalistId + '">' + seatOptions + '</datalist></label>' +
        '<label>每车预留<input data-role="reserve" type="number" min="1" max="4" value="' + initialReserve + '"></label>' +
        '<label>拆班策略<select data-role="split-strategy"><option value="forbid">禁止拆班</option><option value="whole" selected>整班优先</option><option value="balanced">灵活混排</option></select></label>' +
        '<label>状态<input data-role="status" value="系统建议" readonly></label>' +
      '</div>' +
      '<div class="dispatch-plan-tabs"><button type="button" class="dispatch-plan-tab active" data-plan="uniform"><b>统一车型</b><span>正在计算</span></button><button type="button" class="dispatch-plan-tab" data-plan="mixed"><b>混合车队</b><span>正在计算</span></button></div>' +
      '<details class="dispatch-fleet" data-role="fleet"><summary>配置混合车队可用车型与数量</summary><div class="dispatch-fleet-note">勾选车队可提供的车型；数量留空表示不限。可添加46、47等自定义车型。</div><div class="dispatch-fleet-grid" data-role="fleet-grid"></div><button type="button" class="dispatch-fleet-add" data-role="fleet-add">添加自定义车型</button></details>' +
      '<div data-role="result"></div>' +
      '<div class="dispatch-advisor-actions"><button type="button" class="primary" data-role="apply">确认当前方案并计入交通费</button><button type="button" data-role="print">打印分车执行单</button><button type="button" data-role="manual">人工调整分车人数</button><button type="button" data-role="refresh">重新计算</button></div>';

    function clone(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function renderFleetRows() {
      var grid = container.querySelector('[data-role="fleet-grid"]');
      grid.innerHTML = mixedFleet.map(function(item, index) {
        return '<div class="dispatch-fleet-row" data-fleet-index="' + index + '">' +
          '<input type="checkbox" data-fleet-field="enabled" ' + (item.enabled !== false ? 'checked' : '') + ' aria-label="启用' + item.seats + '座车型">' +
          '<label>座位<input type="number" min="7" max="80" value="' + item.seats + '" data-fleet-field="seats" aria-label="车型座位数"></label>' +
          '<label>数量<input type="number" min="1" value="' + (item.count || '') + '" placeholder="不限" data-fleet-field="count" aria-label="' + item.seats + '座可用数量"></label>' +
          (item.custom ? '<button type="button" class="dispatch-fleet-remove" data-role="fleet-remove" title="删除自定义车型" aria-label="删除' + item.seats + '座车型">×</button>' : '<span></span>') +
          '</div>';
      }).join('');
    }

    function readSource() {
      return typeof config.readInput === 'function' ? config.readInput() : {};
    }

    function commonInput() {
      var source = readSource();
      return {
        classCount: source.classCount,
        studentCount: source.studentCount,
        teacherCount: source.teacherCount,
        leaderCount: source.leaderCount,
        responsibleStaff: source.responsibleStaff,
        projectStaff: source.projectStaff,
        classes: source.classes,
        reserveSeats: readMountedInput(container, '[data-role="reserve"]', initialReserve),
        splitStrategy: readMountedInput(container, '[data-role="split-strategy"]', 'whole')
      };
    }

    function calculatePlans() {
      var common = commonInput();
      var uniformInput = Object.assign({}, common, {
        busTypes: [Math.max(7, intValue(readMountedInput(container, '[data-role="uniform-seat"]', initialSeat)))]
      });
      var mixedInput = Object.assign({}, common, { availableFleet: mixedFleet });
      latestAuto.uniform = buildSuggestion(uniformInput);
      latestAuto.mixed = buildSuggestion(mixedInput);
    }

    function planVehicleText(result) {
      if (!result || !result.ok) return '暂不可用';
      var counts = {};
      result.buses.forEach(function(bus) { counts[bus.seats] = (counts[bus.seats] || 0) + 1; });
      return Object.keys(counts).sort(function(a, b) { return intValue(b) - intValue(a); }).map(function(seats) {
        return seats + '座×' + counts[seats];
      }).join(' + ');
    }

    function resultFor(planName) {
      var base = latestAuto[planName];
      var manual = manualByPlan[planName];
      return manual && manual.assignments ? applyManualAssignments(base, manual.assignments) : base;
    }

    function executionRowsFor(planName, result) {
      executionByPlan[planName] = normalizeExecutionRows(executionByPlan[planName], result && result.buses || []);
      return executionByPlan[planName];
    }

    function syncExecutionFromDom() {
      var rows = executionByPlan[activePlan] || [];
      container.querySelectorAll('[data-execution-field]').forEach(function(input) {
        var row = input.closest('[data-execution-index]');
        var index = row ? intValue(row.dataset.executionIndex) : -1;
        if (!rows[index]) return;
        rows[index][input.dataset.executionField] = String(input.value || '').trim();
      });
    }

    function updateExecutionStatus() {
      var box = container.querySelector('[data-role="execution-status"]');
      if (!box || !latestResult) return;
      var check = validateExecutionRows(latestResult, executionByPlan[activePlan]);
      var missing = check.errors.filter(function(item) { return item.indexOf('未填写随车负责人') >= 0; }).length;
      box.textContent = check.ok ? '已满足执行单打印条件' : (missing ? '还有' + missing + '辆车未填随车负责人' : check.errors[0]);
      box.classList.toggle('ready', check.ok);
    }

    function renderTabs() {
      ['uniform', 'mixed'].forEach(function(name) {
        var button = container.querySelector('[data-plan="' + name + '"]');
        var result = resultFor(name);
        button.classList.toggle('active', activePlan === name);
        button.querySelector('span').textContent = result && result.ok
          ? result.summary.busCount + '辆 · ' + planVehicleText(result)
          : (result && result.message || '暂不可用');
      });
      container.querySelector('[data-role="fleet"]').open = activePlan === 'mixed';
    }

    function render(options) {
      options = options || {};
      if (!options.skipExecutionSync) syncExecutionFromDom();
      if (options.resetManual !== false) manualByPlan = { uniform: null, mixed: null };
      calculatePlans();
      latestResult = resultFor(activePlan);
      var executionRows = executionRowsFor(activePlan, latestResult);
      renderTabs();
      var manual = manualByPlan[activePlan];
      container.querySelector('[data-role="result"]').innerHTML = renderResult(latestResult) + renderExecutionEditor(latestResult, executionRows) + (manual ? renderManualEditor(latestResult, manual.assignments) : '');
      container._dispatchAdvisorResult = latestResult;
      return latestResult;
    }

    function syncManualFromDom() {
      var manual = manualByPlan[activePlan];
      if (!manual) return;
      container.querySelectorAll('[data-manual-field]').forEach(function(input) {
        var classId = input.dataset.manualClass;
        var busIndex = intValue(input.dataset.manualBus);
        if (!manual.assignments[classId]) manual.assignments[classId] = {};
        if (!manual.assignments[classId][busIndex]) manual.assignments[classId][busIndex] = { students: 0, teachers: 0 };
        manual.assignments[classId][busIndex][input.dataset.manualField] = intValue(input.value);
      });
    }

    function emitStateChange(options) {
      if (typeof config.onChange === 'function') config.onChange(getState(), options || {});
    }

    function applySuggestion() {
      syncManualFromDom();
      var result = render({ resetManual: false });
      if (!result.ok) {
        if (config.notify) config.notify(result.message, true);
        return result;
      }
      if (result.valid === false) {
        if (config.notify) config.notify('当前分车方案仍有超载、人数或拆班冲突，请先处理红色提示。', true);
        return result;
      }
      if (config.canApply && !config.canApply()) return result;
      if (typeof config.applyResult === 'function') config.applyResult(result);
      var status = container.querySelector('[data-role="status"]');
      var planName = activePlan === 'uniform' ? '统一车型' : '混合车队';
      status.value = '已套用' + planName + ' ' + result.summary.busCount + ' 辆';
      container.querySelector('[data-role="state"]').textContent = status.value;
      if (config.notify) config.notify('分车结果已确认并计入交通费用', false);
      return result;
    }

    function printSuggestion() {
      syncManualFromDom();
      syncExecutionFromDom();
      var result = render({ resetManual: false });
      if (!result.ok || result.valid === false) {
        if (config.notify) config.notify(result.message || '当前分车方案仍有冲突，暂不能打印。', true);
        return result;
      }
      var executionCheck = validateExecutionRows(result, executionByPlan[activePlan]);
      if (!executionCheck.ok) {
        if (config.notify) config.notify(executionCheck.errors.slice(0, 3).join('；'), true);
        return result;
      }
      var existing = document.querySelector('.dispatch-print-report');
      if (existing) existing.remove();
      var report = document.createElement('section');
      report.className = 'dispatch-print-report';
      report.setAttribute('aria-hidden', 'true');
      report.innerHTML = buildPrintReportHtml(result, {
        meta: typeof config.readPrintMeta === 'function' ? config.readPrintMeta() : {},
        source: readSource(),
        planName: activePlan === 'uniform' ? '统一车型' : '混合车队',
        executionRows: executionCheck.rows
      });
      document.body.appendChild(report);
      document.body.classList.add('dispatch-printing');
      function cleanup() {
        document.body.classList.remove('dispatch-printing');
        if (report.parentNode) report.parentNode.removeChild(report);
        window.removeEventListener('afterprint', cleanup);
      }
      window.addEventListener('afterprint', cleanup);
      setTimeout(function() {
        window.print();
        setTimeout(cleanup, 0);
      }, 50);
      return result;
    }

    function beginManual() {
      var base = latestAuto[activePlan];
      if (!base || !base.ok) {
        if (config.notify) config.notify(base && base.message || '当前方案无法人工调整。', true);
        return;
      }
      manualByPlan[activePlan] = { assignments: seedManualAssignments(base) };
      render({ resetManual: false });
      emitStateChange();
    }

    function getState() {
      syncExecutionFromDom();
      return {
        uniformSeat: intValue(readMountedInput(container, '[data-role="uniform-seat"]', initialSeat)),
        reserveSeats: intValue(readMountedInput(container, '[data-role="reserve"]', initialReserve)),
        splitStrategy: readMountedInput(container, '[data-role="split-strategy"]', 'whole'),
        mixedFleet: clone(mixedFleet),
        activePlan: activePlan,
        manualByPlan: clone(manualByPlan),
        executionByPlan: clone(executionByPlan)
      };
    }

    function setState(state, options) {
      state = state || {};
      container.querySelector('[data-role="uniform-seat"]').value = state.uniformSeat ? intValue(state.uniformSeat) : initialSeat;
      container.querySelector('[data-role="reserve"]').value = state.reserveSeats ? intValue(state.reserveSeats) : initialReserve;
      container.querySelector('[data-role="split-strategy"]').value = ['forbid', 'whole', 'balanced'].indexOf(state.splitStrategy) >= 0 ? state.splitStrategy : 'whole';
      if (Array.isArray(state.mixedFleet) && state.mixedFleet.length) {
        mixedFleet = state.mixedFleet.map(function(item) {
          return { seats: Math.max(7, intValue(item.seats)), enabled: item.enabled !== false, count: item.count ? intValue(item.count) : null, custom: !!item.custom };
        });
      } else mixedFleet = DEFAULT_BUS_TYPES.map(function(seats) { return { seats: seats, enabled: true, count: null, custom: false }; });
      activePlan = state.activePlan === 'mixed' ? 'mixed' : 'uniform';
      manualByPlan = state.manualByPlan ? clone(state.manualByPlan) : { uniform: null, mixed: null };
      executionByPlan = state.executionByPlan ? clone(state.executionByPlan) : { uniform: [], mixed: [] };
      renderFleetRows();
      render({ resetManual: false, skipExecutionSync: true });
      emitStateChange(options || {});
    }

    container.querySelector('[data-role="refresh"]').addEventListener('click', render);
    container.querySelector('[data-role="apply"]').addEventListener('click', applySuggestion);
    container.querySelector('[data-role="print"]').addEventListener('click', printSuggestion);
    container.querySelector('[data-role="manual"]').addEventListener('click', beginManual);
    container.querySelector('[data-role="uniform-seat"]').addEventListener('change', function() { render(); emitStateChange(); });
    container.querySelector('[data-role="reserve"]').addEventListener('change', function() { render(); emitStateChange(); });
    container.querySelector('[data-role="split-strategy"]').addEventListener('change', function() { render(); emitStateChange(); });
    container.querySelector('[data-role="fleet-add"]').addEventListener('click', function() {
      syncExecutionFromDom();
      var preferred = [46, 47].find(function(seats) { return !mixedFleet.some(function(item) { return item.seats === seats; }); }) || 46;
      mixedFleet.push({ seats: preferred, enabled: true, count: 1, custom: true });
      renderFleetRows();
      activePlan = 'mixed';
      render({ skipExecutionSync: true });
      emitStateChange();
    });
    function updateFleetEntry(event) {
      var row = event.target.closest('[data-fleet-index]');
      if (!row) return false;
      var index = intValue(row.dataset.fleetIndex);
      var field = event.target.dataset.fleetField;
      if (!mixedFleet[index] || !field) return false;
      if (field === 'enabled') mixedFleet[index].enabled = !!event.target.checked;
      else if (field === 'count') mixedFleet[index].count = event.target.value === '' ? null : intValue(event.target.value);
      else mixedFleet[index].seats = Math.max(7, intValue(event.target.value));
      return true;
    }
    container.querySelector('[data-role="fleet-grid"]').addEventListener('input', function(event) {
      if (!updateFleetEntry(event)) return;
      render();
      emitStateChange();
    });
    container.querySelector('[data-role="fleet-grid"]').addEventListener('change', function(event) {
      if (!updateFleetEntry(event)) return;
      renderFleetRows();
      render();
      emitStateChange();
    });
    container.querySelector('[data-role="fleet-grid"]').addEventListener('click', function(event) {
      var button = event.target.closest('[data-role="fleet-remove"]');
      if (!button) return;
      var row = button.closest('[data-fleet-index]');
      var index = row ? intValue(row.dataset.fleetIndex) : -1;
      if (!mixedFleet[index]) return;
      mixedFleet.splice(index, 1);
      renderFleetRows();
      render();
      emitStateChange();
    });
    container.querySelector('[data-role="result"]').addEventListener('input', function(event) {
      if (!event.target.dataset.executionField) return;
      syncExecutionFromDom();
      updateExecutionStatus();
      emitStateChange();
    });
    container.querySelector('[data-role="result"]').addEventListener('change', function(event) {
      if (!event.target.dataset.manualField) return;
      var manual = manualByPlan[activePlan];
      if (!manual) return;
      var classId = event.target.dataset.manualClass;
      var busIndex = intValue(event.target.dataset.manualBus);
      if (!manual.assignments[classId]) manual.assignments[classId] = {};
      if (!manual.assignments[classId][busIndex]) manual.assignments[classId][busIndex] = { students: 0, teachers: 0 };
      manual.assignments[classId][busIndex][event.target.dataset.manualField] = intValue(event.target.value);
      render({ resetManual: false });
      emitStateChange();
    });
    container.querySelector('[data-role="result"]').addEventListener('click', function(event) {
      var validate = event.target.closest('[data-role="manual-validate"]');
      if (validate) {
        syncManualFromDom();
        render({ resetManual: false });
        emitStateChange();
        return;
      }
      var reset = event.target.closest('[data-role="manual-reset"]');
      if (!reset) return;
      manualByPlan[activePlan] = null;
      render({ resetManual: false });
      emitStateChange();
    });
    container.querySelector('.dispatch-plan-tabs').addEventListener('click', function(event) {
      var button = event.target.closest('[data-plan]');
      if (!button) return;
      syncExecutionFromDom();
      activePlan = button.dataset.plan;
      render({ resetManual: false, skipExecutionSync: true });
      emitStateChange();
    });
    (config.watchIds || []).forEach(function(id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', render);
        el.addEventListener('change', render);
      }
    });
    renderFleetRows();
    render();
    return { render: render, applySuggestion: applySuggestion, printSuggestion: printSuggestion, getState: getState, setState: setState, container: container };
  }

  return {
    DEFAULT_BUS_TYPES: DEFAULT_BUS_TYPES.slice(),
    buildSuggestion: buildSuggestion,
    buildClasses: buildClasses,
    normalizeClasses: normalizeClasses,
    normalizeFleet: normalizeFleet,
    parseClassRows: parseClassRows,
    recommendBuses: recommendBuses,
    effectiveSeats: effectiveSeats,
    buildPrintReportHtml: buildPrintReportHtml,
    normalizeExecutionRows: normalizeExecutionRows,
    validateExecutionRows: validateExecutionRows,
    seedManualAssignments: seedManualAssignments,
    applyManualAssignments: applyManualAssignments,
    mount: mount,
    mountClassRoster: mountClassRoster,
    templateWorkbookRows: templateWorkbookRows
  };
});
